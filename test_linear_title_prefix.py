import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "Lock qualified outputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: Lock qualified outputs",
            },
        )

    def test_prefixes_title_for_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4884",
                "title": "Lock qualified outputs",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: Lock qualified outputs",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4884",
                "title": "Lock qualified outputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: Lock qualified outputs",
            },
        )

    def test_uses_new_status_from_changes_before_current_issue_state(self):
        event = {
            "action": "update",
            "updatedFields": [{"field": "status", "newValue": "To Research"}],
            "data": {
                "issue": {
                    "identifier": "POI-4884",
                    "title": "Lock qualified outputs",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: Lock qualified outputs",
            },
        )

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4884",
            "title": "Lock qualified outputs",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Lock qualified outputs",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4884",
            "title": "Lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_event(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4884",
                "title": "Lock qualified outputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "cursor researching: Lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Lock qualified outputs",
        }
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "Lock qualified outputs",
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
                "issueId": "POI-4884",
                "title": "Cursor researching: Lock qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
