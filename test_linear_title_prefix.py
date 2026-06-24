import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_automation_payload_adds_prefix_for_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4503",
                    "title": "[Trader Site] Unable to close MB due to Comissioning Date for UBA",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4503",
                "title": "Cursor researching: [Trader Site] Unable to close MB due to Comissioning Date for UBA",
            },
        )

    def test_direct_trigger_context_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-123",
                "title": "Investigate certificate export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate certificate export",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4503",
            "title": "Issue still in todo",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trigger_type_can_mark_status_change(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "To Research",
            "id": "POI-124",
            "title": "Trigger type status change",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trigger type status change",
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4503",
            "title": "Comment-only change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4503",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-456",
            "title": "Camel case status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case status",
        )

    def test_nested_linear_update_uses_issue_data_and_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_mapping_can_mark_status_update(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "id": "POI-321",
            "title": "Status in changes",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Status in changes",
        )

    def test_workflow_state_is_supported(self):
        event = {
            "webhookType": "workflowStateChanged",
            "workflowState": {"name": "To Research"},
            "key": "POI-654",
            "title": "Workflow state title",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-654",
        )

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4503",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a payload"))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-999",
            "title": "CLI smoke",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-999",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
