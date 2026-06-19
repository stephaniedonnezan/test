import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_research_prefix_for_cursor_status_change_payload(self):
        event = {
            "automationId": "example-automation",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4443",
                "title": "TypeError: Cannot read properties of null (reading 'meterType')",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4443",
                "title": "Cursor researching: TypeError: Cannot read properties of null (reading 'meterType')",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4443",
                "title": "TypeError: Cannot read properties of null (reading 'meterType')",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4443",
                "title": "TypeError: Cannot read properties of null (reading 'meterType')",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4443",
                "title": "cursor researching: TypeError: Cannot read properties of null",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_spelling_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4443",
                "title": "Investigate null meter type",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate null meter type",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-4443",
                    "title": "Investigate null meter type",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4443",
                "title": "Cursor researching: Investigate null meter type",
            },
        )

    def test_handles_linear_webhook_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "issue-uuid",
                "title": "Investigate null meter type",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate null meter type",
            },
        )

    def test_explicit_new_status_wins_over_nested_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "data": {
                    "id": "POI-4443",
                    "title": "Investigate null meter type",
                    "status": "Backlog",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate null meter type",
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4443",
            "title": "Investigate null meter type",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4443",
            "title": "Investigate null meter type",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4443",
                "title": "Cursor researching: Investigate null meter type",
            },
        )


if __name__ == "__main__":
    unittest.main()
