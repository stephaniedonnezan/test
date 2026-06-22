import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_prefix_for_to_research_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="MB export post QA updates",
                new_status="to research",
            ),
            "Cursor researching - MB export post QA updates",
        )

    def test_status_match_ignores_case_and_extra_whitespace(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="MB export post QA updates",
                new_status="  To   Research ",
            ),
            "Cursor researching - MB export post QA updates",
        )

    def test_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="MB export post QA updates",
                new_status="Triage",
            ),
            "MB export post QA updates",
        )

    def test_does_not_duplicate_existing_marker_with_colon(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Cursor researching: MB export post QA updates",
                new_status="to research",
            ),
            "Cursor researching: MB export post QA updates",
        )

    def test_does_not_duplicate_existing_marker_with_hyphen(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="cursor researching - MB export post QA updates",
                new_status="to research",
            ),
            "cursor researching - MB export post QA updates",
        )

    def test_empty_title_becomes_marker_only(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(title="   ", new_status="to research"),
            "Cursor researching",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_when_status_changed_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "MB export post QA updates",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - MB export post QA updates",
        )

    def test_supports_raw_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - MB export post QA updates",
        )

    def test_supports_status_fallback_field(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "title": "MB export post QA updates",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - MB export post QA updates",
        )

    def test_returns_none_for_non_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "MB export post QA updates",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_status_does_not_match(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Triage",
                "title": "MB export post QA updates",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_title_already_has_marker(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - MB export post QA updates",
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
                "title": "MB export post QA updates",
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
            {"updatedTitle": "Cursor researching - MB export post QA updates"},
        )


if __name__ == "__main__":
    unittest.main()
