from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from docsdelta.cli import main
from docsdelta.config import RunConfig, validate_snapshot


class InputHardeningTests(unittest.TestCase):
    def test_filter_typo_does_not_silently_revert_billing_behavior(self):
        with self.assertRaisesRegex(ValueError, "changed_only"):
            RunConfig.from_dict({"urls": ["https://example.com"], "changed_only": True})
        config = RunConfig.from_dict({"urls": ["https://example.com"], "changedOnly": True, "__platform": True})
        self.assertTrue(config.changed_only)

    def test_snapshot_version_requires_integer_one(self):
        for value in (True, 1.0, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_snapshot({"version": value, "pages": {}})

    def test_deep_json_fails_before_network_with_a_clear_input_error(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text("[" * 2000 + "]" * 2000)
            with patch("docsdelta.cli.run_pipeline") as pipeline, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["--input", str(source), "--output", str(Path(directory) / "out")])
            self.assertEqual(raised.exception.code, 2)
            pipeline.assert_not_called()
