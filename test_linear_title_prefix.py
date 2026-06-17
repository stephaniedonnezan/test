import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4961",
                "title": "Remove Subscribe button on invite",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_ignores_current_todo_trigger_payload(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4961",
                "title": "Remove Subscribe button on invite",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "In Progress",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4961",
            "title": "cursor researching: Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4961",
                    "title": "Remove Subscribe button on invite",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_accepts_changed_status_object(self):
        event = {
            "webhookType": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": {"name": "to-research"}}},
            "issue": {
                "identifier": "POI-4961",
                "title": "Remove Subscribe button on invite",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
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
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )


if __name__ == "__main__":
    unittest.main()
