import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4043",
            "title": "Adjust export generator",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4043",
                "title": "Cursor researching: Adjust export generator",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4043",
                "title": "Adjust export generator",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Adjust export generator",
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4043",
                    "title": "Adjust export generator",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4043",
                "title": "Cursor researching: Adjust export generator",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4043",
            "title": "Adjust export generator",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4043",
            "title": "Adjust export generator",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4043",
            "title": "cursor researching: Adjust export generator",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Adjust export generator",
        )

    def test_accepts_camel_case_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4043",
            "title": "Adjust export generator",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Adjust export generator",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4043",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4043",
            "title": "Adjust export generator",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4043",
                "title": "Cursor researching: Adjust export generator",
            },
        )


if __name__ == "__main__":
    unittest.main()
