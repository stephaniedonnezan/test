import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_cloud_status_change_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5045",
                    "title": '[]Supply contract only states "producer"',
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": 'Cursor researching: []Supply contract only states "producer"',
            },
        )

    def test_normalizes_status_trigger_and_status_value(self):
        event = {
            "triggerType": "linear",
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Mass balance research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Mass balance research",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-2",
                "title": "Supplier evidence checks",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Supplier evidence checks",
            },
        )

    def test_prefers_changed_destination_status_over_current_status(self):
        event = {
            "triggerType": "linear",
            "action": "update",
            "updatedFields": ["status"],
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "status": "Backlog",
            "identifier": "POI-3",
            "title": "Trader contract wording",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Trader contract wording",
            },
        )

    def test_ignores_other_status(self):
        event = {
            "triggerType": "linear",
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4",
            "title": "Trader contract wording",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerType": "linear",
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-5",
            "title": "Trader contract wording",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerType": "linear",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "cursor researching: Trader contract wording",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        event = {
            "triggerType": "linear",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Trader contract wording",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": "Research issue",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Research issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
