import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_research_prefix_for_cursor_status_change_payload(self):
        event = {
            "automationId": "example-automation",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3091",
                "title": "cursor researching: [FE] Dialog refinment",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_spelling_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: [FE] Dialog refinment",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-3091",
                    "title": "[FE] Dialog refinment",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )

    def test_cli_outputs_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            },
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
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )


if __name__ == "__main__":
    unittest.main()
