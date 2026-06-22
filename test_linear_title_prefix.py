import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import derive_updated_title
from linear_title_prefix import updated_title_for_status_change


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_adds_marker_for_to_research_status(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(
                title="when creating an external input to a trader",
                new_status="to research",
            ),
            "Cursor researching - when creating an external input to a trader",
        )

    def test_status_match_is_case_whitespace_and_separator_insensitive(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(
                title="Issue title",
                new_status="  To_Research ",
            ),
            "Cursor researching - Issue title",
        )

    def test_returns_original_title_for_other_statuses(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(
                title="Issue title",
                new_status="QA",
            ),
            "Issue title",
        )

    def test_does_not_duplicate_existing_marker_with_hyphen(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(
                title="Cursor researching - Issue title",
                new_status="to research",
            ),
            "Cursor researching - Issue title",
        )

    def test_does_not_duplicate_existing_marker_with_colon(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(
                title="cursor researching: Issue title",
                new_status="to research",
            ),
            "cursor researching: Issue title",
        )

    def test_empty_titles_become_marker_only(self) -> None:
        self.assertEqual(
            updated_title_for_status_change(title="   ", new_status="to research"),
            "Cursor researching",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_for_status_changed_trigger_context(self) -> None:
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

    def test_supports_direct_trigger_context_payload(self) -> None:
        payload = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_uses_status_field_when_new_status_is_absent(self) -> None:
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

    def test_returns_none_for_non_status_change_triggers(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_status_does_not_match(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payloads(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "bad"}))
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


class CliTests(unittest.TestCase):
    def test_cli_reads_payload_file_and_prints_updated_title(self) -> None:
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
