import asyncio
from dataclasses import replace
from .config import RunConfig
from .pipeline import run_pipeline
from .output import pages_csv, rag_chunks, chunk_operations, ndjson

BILLABLE_EVENT = "page-processed"


async def run_actor():
    from apify import Actor
    async with Actor:
        try:
            config = RunConfig.from_dict(await Actor.get_input() or {})
        except ValueError as exc:
            await Actor.set_value("OUTPUT", {"error": f"Invalid input: {exc}", "results": []})
            Actor.exit_code = 1
            Actor.status_message = f"Invalid input: {exc}"
            return
        manager = Actor.get_charging_manager()
        pricing = manager.get_pricing_info()
        is_ppe = pricing.is_pay_per_event
        if is_ppe and Actor.configuration.is_at_home and BILLABLE_EVENT not in pricing.per_event_prices:
            await Actor.set_value("OUTPUT", {"error": "page-processed billing event is missing.", "results": []})
            Actor.exit_code = 1
            return
        budget_reached = False
        if is_ppe:
            affordable = manager.compute_push_data_limit(config.max_pages, BILLABLE_EVENT, is_default_dataset=True)
            budget_reached = affordable == 0
            config = replace(config, max_pages=max(1, min(config.max_pages, affordable)))

        async def save(row):
            nonlocal budget_reached
            if is_ppe:
                if manager.compute_push_data_limit(1, BILLABLE_EVENT, is_default_dataset=True) < 1:
                    budget_reached = True
                    return False
                charge = await Actor.push_data(row, charged_event_name=BILLABLE_EVENT)
                budget_reached = charge.event_charge_limit_reached or charge.charged_count == 0
                return charge.charged_count > 0
            await Actor.push_data(row)
            return True

        if budget_reached:
            report = {"results": [], "diagnostics": [], "snapshot": config.previous_snapshot,
                "summary": {"savedPages": 0, "requests": 0, "cannotInferDeletions": True}}
        else:
            report = await run_pipeline(config, on_result=save)
        rows = report["results"]
        operations = chunk_operations(rows)
        summary = {**report["summary"], "budgetLimitReached": budget_reached,
            "billingEvent": BILLABLE_EVENT if is_ppe else None,
            "chargedPages": manager.get_charged_event_count(BILLABLE_EVENT) if is_ppe else 0,
            "chunkUpserts": sum(op["operation"] == "UPSERT" for op in operations),
            "chunkRemovals": sum(op["operation"] == "REMOVE" for op in operations)}
        await Actor.set_value("SNAPSHOT", report["snapshot"])
        await Actor.set_value("SUMMARY", summary)
        await Actor.set_value("DIAGNOSTICS", report["diagnostics"])
        await Actor.set_value("RESULTS", rows)
        await Actor.set_value("CHANGES", [row for row in rows if row["status"] != "UNCHANGED"])
        await Actor.set_value("RAG_CHUNKS", rag_chunks(rows))
        await Actor.set_value("CHUNK_OPERATIONS", operations)
        await Actor.set_value("chunk-operations.ndjson", ndjson(operations), content_type="application/x-ndjson; charset=utf-8")
        await Actor.set_value("results.csv", pages_csv(rows), content_type="text/csv; charset=utf-8")
        await Actor.set_value("results.ndjson", ndjson(rows), content_type="application/x-ndjson; charset=utf-8")
        await Actor.set_value("OUTPUT", {"summary": summary, "diagnostics": report["diagnostics"], "results": rows})
        Actor.status_message = f"Saved {len(rows)} document checks. No page removals inferred."


def main():
    asyncio.run(run_actor())


if __name__ == "__main__":
    main()
