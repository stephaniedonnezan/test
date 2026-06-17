import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4968",
                "title": "Multi member interruption screen needs Atmen brand",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": "Cursor researching: Multi member interruption screen needs Atmen brand",
            },
        )

    def test_prefixes_case_insensitive_status_with_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_uses_status_from_linear_changes_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested Linear issue",
                    "state": {"name": "Backlog"},
                },
                "changes": {"state": {"newValue": "To Research"}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_prefers_issue_identifier_over_webhook_event_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4968",
                    "title": "Linear issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": "Cursor researching: Linear issue title",
            },
        )

    def test_uses_nested_state_name_when_state_id_changes(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "changes": {"stateId": {"newValue": "new-state-id"}},
            "data": {
                "issue": {
                    "identifier": "POI-4968",
                    "title": "State id issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": "Cursor researching: State id issue",
            },
        )

    def test_uses_nested_issue_state_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFrom": {"workflowState": "Backlog"},
            "data": {
                "issue": {
                    "id": "lin-issue-id",
                    "title": "Workflow state issue",
                    "workflowState": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin-issue-id",
                "title": "Cursor researching: Workflow state issue",
            },
        )

    def test_skips_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Comment event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_different_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4",
                "title": "Review status issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changed_field_object_list(self):
        event = {
            "action": "update",
            "changedFields": [
                {
                    "field": "workflowState",
                    "newValue": "To Research",
                }
            ],
            "data": {
                "issue": {
                    "identifier": "POI-7",
                    "title": "Changed field object list",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Changed field object list",
            },
        )

    def test_ignores_non_mapping_event(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4968",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4968",
                "title": "Cursor researching: CLI issue",
            },
        )

    def test_cli_prints_nothing_without_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4968",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
