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
            "id": "POI-4310",
            "title": "[]Trading offtakers should be able to report downstream emissions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4310",
                "title": (
                    "Cursor researching: []Trading offtakers should be able to report "
                    "downstream emissions"
                ),
            },
        )

    def test_accepts_cursor_automation_trigger_context_payload(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4310",
                "title": "Trading offtakers should report emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4310",
                "title": "Cursor researching: Trading offtakers should report emissions",
            },
        )

    def test_accepts_issue_updated_event_when_status_field_changed(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4310",
                "title": "Trading offtakers should report emissions",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4310",
                "title": "Cursor researching: Trading offtakers should report emissions",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self) -> None:
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4310",
            "title": "Trading offtakers should report emissions",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trading offtakers should report emissions",
        )

    def test_uses_nested_workflow_state_name(self) -> None:
        event = {
            "trigger": "status_changed",
            "workflowState": {"name": "To Research"},
            "id": "POI-4310",
            "title": "Trading offtakers should report emissions",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trading offtakers should report emissions",
        )

    def test_skips_non_research_status(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4310",
            "title": "Trading offtakers should report emissions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4310",
            "title": "Trading offtakers should report emissions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4310",
            "title": "cursor researching: Trading offtakers should report emissions",
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
                    "id": "POI-4310",
                }
            )
        )

    def test_ignores_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(None))

    def test_compatibility_wrapper_uses_same_handler(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4310",
            "title": "Trading offtakers should report emissions",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


class DirectTitleHelpersTests(unittest.TestCase):
    def test_update_issue_title_for_status_prefixes_to_research(self) -> None:
        self.assertEqual(
            update_issue_title_for_status("Trading offtakers", "  To   Research "),
            "Cursor researching: Trading offtakers",
        )

    def test_update_issue_title_for_status_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            update_issue_title_for_status("Trading offtakers", "Done"),
            "Trading offtakers",
        )

    def test_derive_updated_title_supports_payload_without_issue_id(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Trading offtakers",
            }
        }

        self.assertEqual(derive_updated_title(payload), "Cursor researching: Trading offtakers")

    def test_derive_updated_title_returns_none_when_no_change_needed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching: Trading offtakers",
            }
        }

        self.assertIsNone(derive_updated_title(payload))


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Trading offtakers",
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
            {"updatedTitle": "Cursor researching: Trading offtakers"},
        )


if __name__ == "__main__":
    unittest.main()
