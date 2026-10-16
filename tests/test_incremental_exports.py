"""Index replay and local checkpoint failure boundaries; no external services."""
import asyncio
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from docsdelta.cli import atomic_write, main, read_json
from docsdelta.config import RunConfig, validate_snapshot
from docsdelta.extract import chunk_markdown, extract_document
from docsdelta.output import chunk_operations
from docsdelta.pipeline import compare_document, run_pipeline, snapshot_entry
from docsdelta.transport import FetchError, Page

URL = "https://docs.python.org/3/test.html"
HTML = "<main><h1>Guide</h1><p>Install the package and configure your project environment.</p><h2>Usage</h2><p>Call the function with your application settings.</p></main>"


class FakeClient:
    mapping = {}

    def __init__(self, config): self.requests = 0
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def fetch(self, url, **kwargs):
        self.requests += 1
        value = self.mapping[url]
        if isinstance(value, Exception): raise value
        return value


class OperationTests(unittest.IsolatedAsyncioTestCase):
    async def test_operations_replay_and_refresh_retained_chunk_positions(self):
        FakeClient.mapping = {URL: Page(URL, HTML, 200, "text/html")}
        first = await run_pipeline(RunConfig(urls=[URL]), client_factory=FakeClient)
        first_operations = chunk_operations(first["results"])
        self.assertTrue(all(op["operation"] == "UPSERT" and op["isNewChunk"] for op in first_operations))
        index = {op["id"]: op for op in first_operations}
        usage_before = next(op for op in first_operations if op["heading"] == "Usage")
        updated = HTML.replace("<h2>Usage", "<h2>Before usage</h2><p>This new section is inserted before the retained section.</p><h2>Usage")
        FakeClient.mapping[URL] = Page(URL, updated, 200, "text/html")
        second = await run_pipeline(RunConfig(urls=[URL], previous_snapshot=first["snapshot"]), client_factory=FakeClient)
        operations = chunk_operations(second["results"])
        usage_after = next(op for op in operations if op.get("heading") == "Usage")
        self.assertEqual(usage_after["id"], usage_before["id"])
        self.assertGreater(usage_after["index"], usage_before["index"])
        self.assertFalse(usage_after["isNewChunk"])
        for _ in range(2):
            for op in operations:
                if op["operation"] == "REMOVE": index.pop(op["id"], None)
                else: index[op["id"]] = op
            self.assertEqual(set(index), {c["id"] for c in second["results"][0]["chunks"]})
            self.assertTrue(all(op["pageContentHash"] == second["results"][0]["contentHash"] for op in index.values()))
        self.assertEqual(index[usage_after["id"]]["index"], usage_after["index"])

    async def test_removed_chunks_only_from_saved_complete_same_page(self):
        FakeClient.mapping = {URL: Page(URL, HTML, 200, "text/html")}
        first = await run_pipeline(RunConfig(urls=[URL]), client_factory=FakeClient)
        config = RunConfig(urls=[URL], previous_snapshot=first["snapshot"])
        modified = HTML.replace("Call the function", "Invoke the replacement API")
        FakeClient.mapping[URL] = Page(URL, modified, 200, "text/html")
        second = await run_pipeline(config, client_factory=FakeClient)
        operations = chunk_operations(second["results"])
        removes = [op for op in operations if op["operation"] == "REMOVE"]
        self.assertEqual([op["id"] for op in removes], second["results"][0]["removedChunkIds"])
        self.assertTrue(removes)
        self.assertTrue(all(op["sourceUrl"] == URL for op in removes))
        self.assertEqual(operations[:len(removes)], removes)
        original = copy.deepcopy(first["snapshot"])
        for value in [FetchError("http_error", "Not found", 404), Page(URL, "<main>short</main>", 200, "text/html")]:
            FakeClient.mapping[URL] = value
            report = await run_pipeline(config, client_factory=FakeClient)
            self.assertEqual(chunk_operations(report["results"]), [])
            self.assertEqual(report["snapshot"], original)
        FakeClient.mapping[URL] = Page(URL, modified, 200, "text/html")
        report = await run_pipeline(config, on_result=AsyncMock(return_value=False), client_factory=FakeClient)
        self.assertEqual(chunk_operations(report["results"]), [])
        self.assertEqual(report["snapshot"], original)

    async def test_saved_and_filtered_unchanged_both_emit_no_operations(self):
        FakeClient.mapping = {URL: Page(URL, HTML, 200, "text/html")}
        first = await run_pipeline(RunConfig(urls=[URL]), client_factory=FakeClient)
        for changed_only in [False, True]:
            report = await run_pipeline(RunConfig(urls=[URL], previous_snapshot=first["snapshot"], changed_only=changed_only), client_factory=FakeClient)
            self.assertEqual(len(report["results"]), 0 if changed_only else 1)
            self.assertEqual(chunk_operations(report["results"]), [])

    async def test_failed_other_page_does_not_generate_removals(self):
        other = "https://docs.python.org/other.html"
        FakeClient.mapping = {URL: Page(URL, HTML, 200, "text/html"), other: Page(other, HTML, 200, "text/html")}
        first = await run_pipeline(RunConfig(urls=[URL, other]), client_factory=FakeClient)
        FakeClient.mapping[URL] = Page(URL, HTML.replace("Call the function", "Invoke the new API"), 200, "text/html")
        FakeClient.mapping[other] = FetchError("http_error", "Not found", 404)
        report = await run_pipeline(RunConfig(urls=[URL, other], previous_snapshot=first["snapshot"]), client_factory=FakeClient)
        self.assertTrue(chunk_operations(report["results"]))
        self.assertTrue(all(op["sourceUrl"] == URL for op in chunk_operations(report["results"])))
        self.assertEqual(report["snapshot"]["pages"][other], first["snapshot"]["pages"][other])


class FenceTests(unittest.TestCase):
    def test_shorter_inner_code_fence_does_not_create_false_heading(self):
        markdown = "# Real\n\n````markdown\n```python\n# Heading inside code\n```\n````\n\n## Next\n\nActual documentation."
        chunks = chunk_markdown(markdown, URL, 1800)
        self.assertEqual([c["heading"] for c in chunks], ["Real", "Next"])
        self.assertIn("# Heading inside code", chunks[0]["text"])


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "input.json"
        self.input.write_text(json.dumps({"urls": [URL], "changedOnly": True}), encoding="utf-8")
        doc = extract_document(HTML, URL, RunConfig())
        row = {"url": URL, "finalUrl": URL, "observedAt": "2026-10-16T00:00:00Z", **doc, **compare_document(doc, None)}
        self.report = {"results": [row], "snapshot": {"version": 1, "pages": {URL: snapshot_entry(doc)}}, "summary": {"savedPages": 1}, "diagnostics": []}
        self.state = self.root / "state" / "snapshot.json"
        self.output = self.root / "output"

    def run_cli(self, extra, report=None):
        crawler = AsyncMock(return_value=copy.deepcopy(report or self.report))
        with patch("docsdelta.cli.run_pipeline", crawler), patch("sys.stdout", new=io.StringIO()):
            main(["--input", str(self.input), "--output", str(self.output), *extra])
        return crawler.call_args.args[0]

    def test_checkpoint_bootstrap_and_subsequent_load(self):
        first_config = self.run_cli(["--snapshot-file", str(self.state)])
        self.assertEqual(first_config.previous_snapshot["pages"], {})
        self.assertEqual(validate_snapshot(json.loads(self.state.read_text())), self.report["snapshot"])
        second_config = self.run_cli(["--snapshot-file", str(self.state)])
        self.assertEqual(second_config.previous_snapshot, self.report["snapshot"])
        operations = [json.loads(line) for line in (self.output / "chunk-operations.ndjson").read_text().splitlines()]
        self.assertEqual(operations, chunk_operations(self.report["results"]))

    def test_read_only_previous_snapshot_and_output_checkpoint(self):
        self.state.parent.mkdir()
        original = json.dumps({"version": 1, "pages": {}})
        self.state.write_text(original)
        config = self.run_cli(["--previous-snapshot", str(self.state)])
        self.assertEqual(config.previous_snapshot["pages"], {})
        self.assertEqual(self.state.read_text(), original)
        self.run_cli(["--snapshot-file", str(self.output / "snapshot.json")])
        self.assertEqual(json.loads((self.output / "snapshot.json").read_text()), self.report["snapshot"])

    def test_export_failure_never_replaces_checkpoint(self):
        self.state.parent.mkdir()
        original = json.dumps({"version": 1, "pages": {}})
        self.state.write_text(original)
        real_write = atomic_write
        def fail_csv(path, value):
            if path.name == "results.csv": raise OSError("simulated full disk")
            real_write(path, value)
        with patch("docsdelta.cli.atomic_write", side_effect=fail_csv), patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
            self.run_cli(["--snapshot-file", str(self.state)])
        self.assertEqual(self.state.read_text(), original)
        self.assertFalse((self.output / "snapshot.json").exists())

    def test_atomic_replace_failure_keeps_old_file_and_cleans_temp(self):
        target = self.root / "checkpoint.json"
        target.write_text("old baseline")
        with patch.object(Path, "replace", side_effect=PermissionError("locked")), self.assertRaises(OSError):
            atomic_write(target, "new baseline")
        self.assertEqual(target.read_text(), "old baseline")
        self.assertEqual(list(self.root.glob(".docsdelta-*.tmp")), [])

    def test_snapshot_conflict_and_missing_file_fail_before_network(self):
        self.input.write_text(json.dumps({"urls": [URL], "previousSnapshot": self.report["snapshot"]}))
        for extra in [["--snapshot-file", str(self.state)], ["--previous-snapshot", str(self.root / "missing.json")]]:
            with patch("docsdelta.cli.run_pipeline", new=AsyncMock()) as crawler, patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
                main(["--input", str(self.input), *extra])
            crawler.assert_not_called()
        self.input.write_text(json.dumps({"urls": [URL]}))
        with patch("docsdelta.cli.run_pipeline", new=AsyncMock()) as crawler, patch("sys.stderr", new=io.StringIO()) as stderr, self.assertRaises(SystemExit):
            main(["--input", str(self.input), "--previous-snapshot", str(self.root / "missing.json")])
        crawler.assert_not_called()
        self.assertIn("missing.json", stderr.getvalue())

    def test_conflicting_checkpoint_target_fails_before_network(self):
        for target in [self.input, self.output / "results.json"]:
            with patch("docsdelta.cli.run_pipeline", new=AsyncMock()) as crawler, patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
                main(["--input", str(self.input), "--output", str(self.output), "--snapshot-file", str(target)])
            crawler.assert_not_called()

    def test_oversized_file_is_rejected_without_loading_whole_file(self):
        path = self.root / "large.json"
        path.write_text(" " * 11)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            read_json(path, 10)


if __name__ == "__main__": unittest.main()
