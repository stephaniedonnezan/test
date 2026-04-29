import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_issue_title import prefix_research_title
from linear_issue_title import title_for_status_change


class PrefixResearchTitleTests(unittest.TestCase):
    def test_adds_cursor_researching_prefix(self) -> None:
        self.assertEqual(
            prefix_research_title("[]exportMB"),
            "Cursor researching - []exportMB",
        )

    def test_trims_title_when_prefixing(self) -> None:
        self.assertEqual(
            prefix_research_title("  Export mass balance  "),
            "Cursor researching - Export mass balance",
        )

    def test_does_not_duplicate_existing_hyphen_prefix(self) -> None:
        self.assertEqual(
            prefix_research_title("Cursor researching - Export mass balance"),
            "Cursor researching - Export mass balance",
        )

    def test_does_not_duplicate_existing_colon_prefix(self) -> None:
        self.assertEqual(
            prefix_research_title("cursor researching: Export mass balance"),
            "cursor researching: Export mass balance",
        )

    def test_empty_title_becomes_prefix_only(self) -> None:
        self.assertEqual(prefix_research_title("   "), "Cursor researching")


class TitleForStatusChangeTests(unittest.TestCase):
    def test_returns_prefixed_title_for_to_research_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]exportMB",
            }
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching - []exportMB",
        )

    def test_status_match_ignores_case_and_extra_whitespace(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "  To   Research ",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching - Issue title",
        )

    def test_trigger_match_accepts_human_readable_variants(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_status_fallback_field(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_flat_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching - Issue title",
        )

    def test_returns_none_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "title": "Issue title",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_for_other_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_when_title_already_has_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Issue title",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_for_missing_required_fields(self) -> None:
        self.assertIsNone(title_for_status_change({"triggerContext": {}}))
        self.assertIsNone(title_for_status_change({"triggerContext": "invalid"}))


class CliTests(unittest.TestCase):
    script_path = Path(__file__).resolve().parent / "linear_issue_title.py"

    def test_cli_reads_input_file_and_writes_updated_title_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(self.script_path), "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - Issue title"},
        )

    def test_cli_reads_stdin(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        result = subprocess.run(
            [sys.executable, str(self.script_path)],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - Issue title"},
        )


if __name__ == "__main__":
    unittest.main()
