import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5043",
            "title": "Add address fetcher to offtaker creation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Add address fetcher to offtaker creation",
            },
        )

    def test_prefixes_wrapped_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5043",
                "title": "Add address fetcher to offtaker creation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Add address fetcher to offtaker creation",
            },
        )

    def test_supports_status_name_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "identifier": "POI-5043",
            "title": "Add address fetcher to offtaker creation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add address fetcher to offtaker creation",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5043",
            "title": "Add address fetcher to offtaker creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5043",
            "title": "Add address fetcher to offtaker creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5043",
            "title": "cursor researching: Add address fetcher to offtaker creation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5043",
                    "title": "Add address fetcher to offtaker creation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Add address fetcher to offtaker creation",
            },
        )

    def test_supports_nested_linear_changes_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5043",
                    "title": "Add address fetcher to offtaker creation",
                }
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add address fetcher to offtaker creation",
        )

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5043"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5043",
            "title": "Add address fetcher to offtaker creation",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Add address fetcher to offtaker creation",
            },
        )


if __name__ == "__main__":
    unittest.main()
