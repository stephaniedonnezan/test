import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title
from linear_title_prefix import handle_issue_status_changed
from linear_title_prefix import update_issue_title_for_status


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3838",
            "title": "Audit creation: ask for a scope",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3838",
                "title": "Cursor researching: Audit creation: ask for a scope",
            },
        )

    def test_accepts_cursor_automation_trigger_context_payload(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3838",
                "title": "Audit creation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3838",
                "title": "Cursor researching: Audit creation",
            },
        )

    def test_accepts_issue_updated_event_when_status_field_changed(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-3838",
                "title": "Audit creation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3838",
                "title": "Cursor researching: Audit creation",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self) -> None:
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-3838",
            "title": "Audit creation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Audit creation",
        )

    def test_uses_nested_workflow_state_name(self) -> None:
        event = {
            "trigger": "status_changed",
            "workflowState": {"name": "To Research"},
            "id": "POI-3838",
            "title": "Audit creation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Audit creation",
        )

    def test_skips_non_research_status(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3838",
            "title": "Audit creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3838",
            "title": "Audit creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3838",
            "title": "cursor researching: Audit creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3838",
                }
            )
        )

    def test_ignores_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(None))

    def test_compatibility_wrapper_uses_same_handler(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3838",
            "title": "Audit creation",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


class DirectTitleHelpersTests(unittest.TestCase):
    def test_update_issue_title_for_status_prefixes_to_research(self) -> None:
        self.assertEqual(
            update_issue_title_for_status("Audit creation", "  To   Research "),
            "Cursor researching: Audit creation",
        )

    def test_update_issue_title_for_status_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(update_issue_title_for_status("Audit creation", "Done"), "Audit creation")

    def test_derive_updated_title_supports_payload_without_issue_id(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Audit creation",
            }
        }

        self.assertEqual(derive_updated_title(payload), "Cursor researching: Audit creation")

    def test_derive_updated_title_returns_none_when_no_change_needed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching: Audit creation",
            }
        }

        self.assertIsNone(derive_updated_title(payload))


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Audit creation",
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
            {"updatedTitle": "Cursor researching: Audit creation"},
        )


if __name__ == "__main__":
    unittest.main()
