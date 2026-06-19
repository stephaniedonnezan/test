import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4307",
                    "title": "Spreadsheet app agnostic for testing",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4307",
                "title": "Cursor researching: Spreadsheet app agnostic for testing",
            },
        )

    def test_direct_trigger_context_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "issueId": "POI-123",
                "title": "Investigate flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate flow",
            },
        )

    def test_nested_linear_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-456",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_generic_update_uses_changed_status_value(self):
        event = {
            "type": "update",
            "issue": {
                "id": "POI-789",
                "title": "Changed status",
            },
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "to_research"},
                }
            },
            "newStatus": "to-research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Changed status",
            },
        )

    def test_skips_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-111",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-222",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_changed_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-333",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-444",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-555",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-666",
            "title": "CLI issue",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-666",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
