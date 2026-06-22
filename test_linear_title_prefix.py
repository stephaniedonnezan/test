import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_supports_cloud_automation_trigger_context_shape(self):
        event = {
            "automation_trigger_info": {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4579",
                    "title": "MB export corrections",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4579",
                    "title": "MB export corrections",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_reads_status_from_change_map_before_current_issue_status(self):
        event = {
            "action": "updated",
            "data": {
                "issue": {
                    "identifier": "POI-4579",
                    "title": "MB export corrections",
                }
            },
            "changes": {
                "workflowState": {
                    "oldValue": "Backlog",
                    "newValue": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_even_if_status_is_to_research(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-4579",
            "title": "MB export corrections",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4579",
            "title": "cursor researching: MB export corrections",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "cursor researching: MB export corrections",
            },
        )

    def test_handles_camel_case_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4579",
            "title": "  MB export corrections  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_handler_alias_matches_primary_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )


if __name__ == "__main__":
    unittest.main()
