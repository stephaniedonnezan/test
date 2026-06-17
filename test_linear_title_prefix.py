import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4970",
                "title": "Changing from POS issuer role to User Role does not remove ability to close POSes",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4970",
                "title": "Cursor researching: Changing from POS issuer role to User Role does not remove ability to close POSes",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-123",
            "title": "Investigate user permissions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate user permissions",
            },
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Review balance export",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Review balance export",
            },
        )

    def test_supports_workflow_state_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": "To Research"}},
            "data": {
                "id": "POI-789",
                "title": "Research settlement issue",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Research settlement issue",
            },
        )

    def test_supports_status_value_from_changes_metadata(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Todo", "newValue": "To Research"}},
            "data": {
                "id": "POI-790",
                "title": "Research issuer permissions",
                "status": {"name": "Todo"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-790",
                "title": "Cursor researching: Research issuer permissions",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4970",
            "title": "Changing from POS issuer role to User Role does not remove ability to close POSes",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4970",
            "title": "Changing from POS issuer role to User Role does not remove ability to close POSes",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4970",
            "title": "cursor researching: Existing investigation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_events_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Investigate missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_events_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4970",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_matching_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4970",
            "title": "Investigate POS permission",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4970",
                "title": "Cursor researching: Investigate POS permission",
            },
        )


if __name__ == "__main__":
    unittest.main()
