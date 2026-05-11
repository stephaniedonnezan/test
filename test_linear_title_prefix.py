import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4589",
            "title": "Work to get the UBA template working for CH4",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4589",
                "title": "Cursor researching: Work to get the UBA template working for CH4",
            },
        )

    def test_accepts_automation_trigger_context_shape(self) -> None:
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Fix the issue, make the test be green",
                "id": "POI-4589",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4589",
                "title": "Cursor researching: Fix the issue, make the test be green",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4589",
                "title": "Investigate UBA export",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4589",
                "title": "Cursor researching: Investigate UBA export",
            },
        )

    def test_accepts_camel_case_status(self) -> None:
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4589",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate UBA export",
        )

    def test_uses_state_name_when_status_is_nested(self) -> None:
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4589",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate UBA export",
        )

    def test_derives_updated_title_for_title_only_callers(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4589",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            derive_updated_title(event),
            "Cursor researching: Investigate UBA export",
        )

    def test_skips_non_research_status(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4589",
            "title": "Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4589",
            "title": "Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4589",
            "title": " cursor researching: Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4589"}
            )
        )

    def test_ignores_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(None))


class CliTest(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
                "id": "POI-4589",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(event), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4589",
                "title": "Cursor researching: Issue title",
            },
        )


if __name__ == "__main__":
    unittest.main()
