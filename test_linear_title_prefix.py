import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_cursor_trigger_context_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4660",
                "title": "Site switch on the site name",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4660",
                "title": "Cursor researching: Site switch on the site name",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-123",
            "title": "Investigate import flow",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate import flow",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "status": "to research",
            "id": "POI-123",
            "title": "Investigate import flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate import flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-123",
            "title": "cursor researching: Investigate import flow",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Investigate import flow",
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-123",
                "title": "Investigate import flow",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate import flow",
            },
        )

    def test_uses_nested_issue_from_data(self):
        event = {
            "webhookType": "issue",
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Investigate import flow",
                    "workflowState": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-123",
        )

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research", "id": "POI-123"}

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate import flow",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate import flow",
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
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate import flow",
            },
        )


if __name__ == "__main__":
    unittest.main()
