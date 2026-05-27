import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4533",
                "title": "[Error in test.Atmen] Shell HH1 Trading - January 2025",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4533",
                "title": "Cursor researching: [Error in test.Atmen] Shell HH1 Trading - January 2025",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Triage",
                "id": "POI-4533",
                "title": "Investigate Shell report",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4533",
                "title": "Investigate Shell report",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4533",
                "title": "cursor researching: Investigate Shell report",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "identifier": "POI-4533",
                "title": "Investigate Shell report",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4533",
                "title": "Cursor researching: Investigate Shell report",
            },
        )

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4533",
                "title": "Investigate Shell report",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate Shell report",
            },
        )

    def test_uses_nested_issue_id_before_outer_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "title": "Investigate Shell report",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate Shell report",
            },
        )

    def test_supports_workflow_state_fields(self):
        event = {
            "type": "Issue Updated",
            "updated_fields": {"workflowState": {"name": "To Research"}},
            "issue": {
                "issueId": "POI-4533",
                "title": "Investigate Shell report",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4533",
                "title": "Cursor researching: Investigate Shell report",
            },
        )

    def test_ignores_update_payloads_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4533",
                "title": "Investigate Shell report",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate Shell report",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4533",
                "title": "Investigate Shell report",
            }
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
                "issueId": "POI-4533",
                "title": "Cursor researching: Investigate Shell report",
            },
        )


if __name__ == "__main__":
    unittest.main()
