import argparse
import asyncio
import json
from pathlib import Path
from .config import RunConfig
from .pipeline import run_pipeline
from .output import pages_csv, rag_chunks, ndjson


def main():
    parser = argparse.ArgumentParser(description="Public docs → Markdown, chunks, and explicit change feed.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    try:
        config = RunConfig.from_dict(json.loads(args.input.read_text(encoding="utf-8-sig")))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    report = asyncio.run(run_pipeline(config))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in [("results.json", report["results"]), ("snapshot.json", report["snapshot"]),
        ("diagnostics.json", report["diagnostics"]), ("summary.json", report["summary"]), ("rag-chunks.json", rag_chunks(report["results"]))]:
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "results.csv").write_text(pages_csv(report["results"]), encoding="utf-8")
    (args.output / "results.ndjson").write_text(ndjson(report["results"]), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
