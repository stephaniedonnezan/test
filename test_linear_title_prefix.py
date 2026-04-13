import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_prefix_for_to_research(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Display total CO2e and total GO on export",
                new_status="to research",
            ),
            "Cursor researching - Display total CO2e and total GO on export",
        )

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="  To   Research ",
            ),
            "Cursor researching - Some issue",
        )

    def test_no_change_for_other_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="In Review",
            ),
            "Some issue",
        )

    def test_does_not_duplicate_existing_prefix_colon(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Cursor researching: Some issue",
                new_status="to research",
            ),
            "Cursor researching: Some issue",
        )

    def test_does_not_duplicate_existing_prefix_hyphen(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="cursor researching - Some issue",
                new_status="to research",
            ),
            "cursor researching - Some issue",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_when_payload_matches(self) -> None:
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

    def test_returns_none_for_non_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_no_update_needed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payload(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "bad"}))
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
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
