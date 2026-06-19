import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_to_research_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3610",
                "title": "Create a function to auto assign end-trip activity",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function to auto assign end-trip activity",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-3610",
                "title": "Create a function",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_with_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3610",
                "title": "Create a function",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-3610",
            "title": "cursor researching: Create a function",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_target_status_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "ToResearch",
            "issue_id": "POI-3610",
            "title": "  Create a function  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function",
            },
        )

    def test_handles_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3610",
                    "title": "Create a function",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function",
            },
        )

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-3610",
                    "title": "Create a function",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_from_changes_payload(self):
        event = {
            "action": "updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "to_research"}},
            "identifier": "POI-3610",
            "title": "Create a function",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3610",
            "title": "Create a function",
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
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function",
            },
        )


if __name__ == "__main__":
    unittest.main()
