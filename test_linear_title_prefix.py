import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_status_changed_to_research_prefixes_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5009",
                "title": "Creating a delivery in the traceability view is not possible",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5009",
                "title": "Cursor researching: Creating a delivery in the traceability view is not possible",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-123",
            "title": "Needs investigation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Needs investigation",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5009",
            "title": "Creating a delivery in the traceability view is not possible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5009",
            "title": "Creating a delivery in the traceability view is not possible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5009",
            "title": "cursor researching: Creating a delivery in the traceability view is not possible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5009",
                    "title": "Creating a delivery in the traceability view is not possible",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5009",
                "title": "Cursor researching: Creating a delivery in the traceability view is not possible",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5009",
            "title": "Creating a delivery in the traceability view is not possible",
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
                "issueId": "POI-5009",
                "title": "Cursor researching: Creating a delivery in the traceability view is not possible",
            },
        )


if __name__ == "__main__":
    unittest.main()
