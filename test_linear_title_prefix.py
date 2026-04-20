import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import has_prefix, should_prefix, update_title


class ShouldPrefixTests(unittest.TestCase):
    def test_true_for_status_changed_to_to_research(self) -> None:
        payload = {"trigger": "status_changed", "newStatus": "to research"}
        self.assertTrue(should_prefix(payload))

    def test_true_for_status_with_spaces_and_case(self) -> None:
        payload = {"trigger": "Status Changed", "newStatus": "To Research"}
        self.assertTrue(should_prefix(payload))

    def test_false_for_other_trigger(self) -> None:
        payload = {"trigger": "issue_updated", "newStatus": "to research"}
        self.assertFalse(should_prefix(payload))

    def test_false_for_other_status(self) -> None:
        payload = {"trigger": "status_changed", "newStatus": "dev"}
        self.assertFalse(should_prefix(payload))

    def test_status_fallback_when_new_status_missing(self) -> None:
        payload = {"trigger": "status_changed", "status": "to research"}
        self.assertTrue(should_prefix(payload))


class HasPrefixTests(unittest.TestCase):
    def test_detects_dash_prefix(self) -> None:
        self.assertTrue(has_prefix("Cursor researching - Issue title"))

    def test_detects_colon_prefix(self) -> None:
        self.assertTrue(has_prefix("cursor researching: Issue title"))

    def test_false_for_non_prefixed(self) -> None:
        self.assertFalse(has_prefix("Issue title"))


class UpdateTitleTests(unittest.TestCase):
    def test_adds_prefix_once(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "[Bug] Missing site ID",
        }
        self.assertEqual(
            update_title(payload),
            "Cursor researching - [Bug] Missing site ID",
        )

    def test_keeps_existing_prefix(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Cursor researching - [Bug] Missing site ID",
        }
        self.assertEqual(
            update_title(payload),
            "Cursor researching - [Bug] Missing site ID",
        )

    def test_no_change_when_not_matching(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "dev",
            "title": "[Bug] Missing site ID",
        }
        self.assertEqual(update_title(payload), "[Bug] Missing site ID")

    def test_empty_title_returns_empty(self) -> None:
        payload = {"trigger": "status_changed", "newStatus": "to research", "title": ""}
        self.assertEqual(update_title(payload), "")


class CliTests(unittest.TestCase):
    def test_cli_reads_file_and_prints_json(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "[Bug] Missing site ID",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "payload.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(input_path)],
                cwd=Path(__file__).resolve().parent,
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - [Bug] Missing site ID"},
        )


if __name__ == "__main__":
    unittest.main()
