import argparse
import asyncio
import json
import os
from pathlib import Path
import tempfile
from .config import RunConfig
from .pipeline import run_pipeline
from .output import pages_csv, rag_chunks, chunk_operations, ndjson

MAX_INPUT_BYTES = 6 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024


def read_json(path: Path, max_bytes: int):
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"{path}: JSON file exceeds the {max_bytes}-byte limit.")
    return json.loads(raw.decode("utf-8-sig"))


def atomic_write(path: Path, value: str):
    """Replace one completed export without leaving a truncated checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                prefix=".docsdelta-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Public docs → Markdown, chunks, and explicit change feed.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output"))
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument("--previous-snapshot", type=Path, help="Load a previous SNAPSHOT JSON; this file is not updated unless it is an output path.")
    baseline.add_argument("--snapshot-file", type=Path, help="Load a local checkpoint if present, then atomically replace it after all exports finish. Missing file starts a new baseline.")
    args = parser.parse_args(argv)
    try:
        data = read_json(args.input, MAX_INPUT_BYTES)
        snapshot_path = args.previous_snapshot or args.snapshot_file
        if snapshot_path:
            if not isinstance(data, dict):
                raise ValueError("Input must be a JSON object.")
            if data.get("previousSnapshot") not in (None, {"version": 1, "pages": {}}):
                raise ValueError("Choose either previousSnapshot in the input or a snapshot file flag, not both.")
            if args.previous_snapshot or snapshot_path.exists():
                data["previousSnapshot"] = read_json(snapshot_path, MAX_SNAPSHOT_BYTES)
        config = RunConfig.from_dict(data)
        reserved = {"results.json", "diagnostics.json", "summary.json", "rag-chunks.json", "chunk-operations.json", "results.csv", "results.ndjson", "chunk-operations.ndjson"}
        if args.snapshot_file and args.snapshot_file.resolve() == args.input.resolve():
            raise ValueError("--snapshot-file must not overwrite the input configuration file.")
        if args.snapshot_file and args.snapshot_file.resolve() in {(args.output / name).resolve() for name in reserved}:
            raise ValueError("--snapshot-file must be separate from result exports; use state/snapshot.json or output/snapshot.json.")
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        parser.error(str(exc))
    report = asyncio.run(run_pipeline(config))
    rows = report["results"]
    operations = chunk_operations(rows)
    report["summary"].update(chunkUpserts=sum(op["operation"] == "UPSERT" for op in operations),
        chunkRemovals=sum(op["operation"] == "REMOVE" for op in operations))
    try:
        for name, value in [("results.json", rows), ("diagnostics.json", report["diagnostics"]),
            ("summary.json", report["summary"]), ("rag-chunks.json", rag_chunks(rows)), ("chunk-operations.json", operations)]:
            atomic_write(args.output / name, json.dumps(value, ensure_ascii=False, indent=2))
        atomic_write(args.output / "results.csv", pages_csv(rows))
        atomic_write(args.output / "results.ndjson", ndjson(rows))
        atomic_write(args.output / "chunk-operations.ndjson", ndjson(operations))
        # A compact snapshot uses the same JSON representation as the 5 MiB bound.
        snapshot_json = json.dumps(report["snapshot"], ensure_ascii=False)
        atomic_write(args.output / "snapshot.json", snapshot_json)
        if args.snapshot_file and args.snapshot_file.resolve() != (args.output / "snapshot.json").resolve():
            atomic_write(args.snapshot_file, snapshot_json)
    except OSError as exc:
        parser.error(f"Could not finish exports: {exc}. Checkpoint may not have advanced; inspect the files and retry from the last confirmed baseline.")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
