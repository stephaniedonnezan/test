import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import add_research_marker
from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class AddResearchMarkerTests(unittest.TestCase):
    def test_adds_marker_to_title(self) -> None:
        self.assertEqual(
            add_research_marker("MB allocation: Ensure no leftover volume"),
            "Cursor researching - MB allocation: Ensure no leftover volume",
        )

    def test_returns_marker_for_blank_title(self) -> None:
        self.assertEqual(add_research_marker("   "), "Cursor researching")

    def test_does_not_duplicate_existing_marker_with_hyphen(self) -> None:
        self.assertEqual(
            add_research_marker("Cursor researching - Some issue"),
            "Cursor researching - Some issue",
        )

    def test_does_not_duplicate_existing_marker_with_colon_or_case_change(self) -> None:
        self.assertEqual(
            add_research_marker("cursor researching: Some issue"),
            "cursor researching: Some issue",
        )


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_marker_for_to_research_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="MB allocation: Ensure no leftover volume",
                new_status="to research",
            ),
            "Cursor researching - MB allocation: Ensure no leftover volume",
        )

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="  To   Research ",
            ),
            "Cursor researching - Some issue",
        )

    def test_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="Done",
            ),
            "Some issue",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_for_trigger_context_payload(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
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
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_status_object_name(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": {"name": "to research"},
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_raw_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_returns_none_for_non_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_no_update_is_needed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payload(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "invalid"}))
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_updated_title_json(self) -> None:
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
                [sys.executable, "linear_title_prefix.py", "--input", str(payload_path)],
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
