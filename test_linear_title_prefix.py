import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_trigger_when_status_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "Normalize delivery transport segments",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Normalize delivery transport segments",
            },
        )

    def test_accepts_status_fallback_from_flat_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to_research",
                "issueId": "POI-1",
                "title": "  Find emission source  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Find emission source",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-2",
                "title": "Implement model change",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "Research issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "cursor researching: Research issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "toResearch",
                "id": "POI-5",
                "title": "Research issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "lin_123",
                "title": "Research issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin_123",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_handles_nested_updated_from_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"workflowState": "Backlog"},
            "data": {
                "identifier": "POI-6",
                "title": "Research issue",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_ignores_linear_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "lin_456",
                "title": "Research issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": "Research issue",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Research issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
