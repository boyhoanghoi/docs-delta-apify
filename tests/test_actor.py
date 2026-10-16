"""Billing boundary tests use an in-memory Actor; no account or network needed."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from decimal import Decimal
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from docsdelta.actor import BILLABLE_EVENT, run_actor
from docsdelta.config import RunConfig
from docsdelta.extract import extract_document
from docsdelta.pipeline import compare_document


class FakeManager:
    def __init__(self, remaining=2, ppe=True):
        self.remaining = remaining
        self.count = 0
        self.ppe = ppe

    def get_pricing_info(self):
        return SimpleNamespace(is_pay_per_event=self.ppe, per_event_prices={BILLABLE_EVENT: Decimal("0.003")})

    def compute_push_data_limit(self, count, event, *, is_default_dataset):
        return min(count, self.remaining)

    def get_charged_event_count(self, event):
        return self.count


class FakeActor:
    def __init__(self, manager, data=None):
        self.manager = manager
        self.input = data or {"urls": ["https://one.business.co", "https://two.business.co", "https://three.business.co"]}
        self.dataset = []
        self.writes = {}
        self.events = []
        self.configuration = SimpleNamespace(is_at_home=False)
        self.log = SimpleNamespace(error=lambda message: None, info=lambda message: None)
        self.exit_code = 0
        self.status_message = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get_input(self):
        return self.input

    def get_charging_manager(self):
        return self.manager

    async def set_value(self, key, value, **kwargs):
        self.writes[key] = value

    async def push_data(self, row, charged_event_name=None):
        # Match the relevant SDK persistence-before-explicit-charge boundary.
        if charged_event_name and self.manager.remaining < 1:
            return SimpleNamespace(charged_count=0, event_charge_limit_reached=True)
        self.dataset.append(row)
        self.events.append(charged_event_name)
        if charged_event_name:
            self.manager.count += 1
            self.manager.remaining -= 1
        return SimpleNamespace(charged_count=1 if charged_event_name else 0,
                               event_charge_limit_reached=self.manager.remaining == 0)


async def fake_crawl(config, on_result):
    saved = []
    for url in config.urls[:config.max_pages]:
        doc = extract_document("<main><h1>Document</h1><p>Source content for the accepted page and its bounded chunk export.</p></main>", url, RunConfig())
        row = {"url": url, "observedAt": "2026-10-16T00:00:00Z", **doc, **compare_document(doc, None)}
        if not await on_result(row):
            break
        saved.append(row)
    return {"results": saved, "snapshot": {"version": 1, "pages": {}}, "diagnostics": [{"url": "https://failed.business.co", "status": "blocked"}],
            "summary": {"savedPages": len(saved), "failedDomains": 1}}


class ActorTests(unittest.IsolatedAsyncioTestCase):
    async def run_fake(self, actor, crawl=fake_crawl):
        with patch.dict(sys.modules, {"apify": SimpleNamespace(Actor=actor)}), patch("docsdelta.actor.run_pipeline", new=crawl):
            await run_actor()

    async def test_paid_limit_keeps_last_saved_result_and_exports_no_extra(self):
        actor = FakeActor(FakeManager(remaining=1))
        await self.run_fake(actor)
        self.assertEqual(len(actor.dataset), 1)
        self.assertEqual(actor.dataset, actor.writes["RESULTS"])
        self.assertEqual(actor.events, [BILLABLE_EVENT])
        self.assertEqual(actor.writes["SUMMARY"]["chargedPages"], 1)
        self.assertTrue(actor.writes["SUMMARY"]["budgetLimitReached"])
        self.assertEqual(actor.writes["SUMMARY"]["savedPages"], 1)
        self.assertEqual(actor.writes["SUMMARY"]["chunkUpserts"], 1)
        self.assertEqual(actor.writes["SUMMARY"]["chunkRemovals"], 0)
        self.assertEqual(len(actor.writes["CHUNK_OPERATIONS"]), 1)
        self.assertEqual(actor.writes["CHUNK_OPERATIONS"][0]["sourceUrl"], actor.dataset[0]["url"])
        self.assertNotIn("two.business.co", actor.writes["results.csv"])
        self.assertNotIn("two.business.co", actor.writes["chunk-operations.ndjson"])
        self.assertEqual(len(actor.writes["DIAGNOSTICS"]), 1)

    async def test_zero_budget_starts_no_crawl_or_charge(self):
        actor = FakeActor(FakeManager(remaining=0))
        crawler = AsyncMock()
        await self.run_fake(actor, crawler)
        crawler.assert_not_awaited()
        self.assertEqual(actor.dataset, [])
        self.assertEqual(actor.events, [])
        self.assertTrue(actor.writes["SUMMARY"]["budgetLimitReached"])
        self.assertEqual(actor.writes["CHUNK_OPERATIONS"], [])
        self.assertEqual(actor.writes["chunk-operations.ndjson"], "")

    async def test_non_ppe_results_have_no_explicit_billing_event(self):
        actor = FakeActor(FakeManager(ppe=False))
        await self.run_fake(actor)
        self.assertEqual(len(actor.dataset), 3)
        self.assertEqual(actor.events, [None, None, None])
        self.assertEqual(actor.writes["SUMMARY"]["chargedPages"], 0)
        self.assertIsNone(actor.writes["SUMMARY"]["billingEvent"])

    async def test_invalid_input_fails_without_billing(self):
        actor = FakeActor(FakeManager(), {"urls": "bad"})
        crawler = AsyncMock()
        await self.run_fake(actor, crawler)
        crawler.assert_not_awaited()
        self.assertEqual(actor.exit_code, 1)
        self.assertIn("Invalid input", actor.writes["OUTPUT"]["error"])
        self.assertEqual(actor.events, [])

    async def test_missing_production_event_fails_before_work(self):
        actor = FakeActor(FakeManager())
        actor.configuration.is_at_home = True
        actor.manager.get_pricing_info = lambda: SimpleNamespace(is_pay_per_event=True, per_event_prices={})
        crawler = AsyncMock()
        await self.run_fake(actor, crawler)
        crawler.assert_not_awaited()
        self.assertEqual(actor.exit_code, 1)
        self.assertIn("missing", actor.writes["OUTPUT"]["error"])


if __name__ == "__main__":
    unittest.main()
