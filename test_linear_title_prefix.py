import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_prefixes_wrapped_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5018",
                "title": "Error alert with repeating txt",
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-5018")
        self.assertEqual(result["title"], "Cursor researching: Error alert with repeating txt")

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-5018",
            "title": "cursor researching: Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5018",
                "title": "Error alert with repeating txt",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_ignores_nested_issue_update_when_status_field_not_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5018",
                "title": "Error alert with repeating txt",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_change_payload(self):
        event = {
            "action": "updated",
            "type": "Issue",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "to-research"}}},
            "data": {
                "identifier": "POI-5018",
                "title": "Error alert with repeating txt",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )


if __name__ == "__main__":
    unittest.main()
