import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_automation_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "GET /automate/sites failed with code: ERR_BAD_REQUEST",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with code: ERR_BAD_REQUEST",
            },
        )

    def test_prefixes_title_from_trigger_context(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed with status code 412",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with status code 412",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4644",
            "title": "Investigate failing sites request",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate failing sites request",
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4644",
                    "title": "Investigate Linear status automation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Linear status automation",
            },
        )

    def test_accepts_change_record_new_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "id": "issue-123",
                    "title": "Research status transition",
                }
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research status transition",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4644",
            "title": "cursor researching: GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4644",
            "title": "GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_event(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "POI-4644",
                    "title": "GET /automate/sites failed",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4644",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_writes_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-4644",
            "title": "GET /automate/sites failed",
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
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )


if __name__ == "__main__":
    unittest.main()
