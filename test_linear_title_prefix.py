import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_for_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "[]Research: source of errors when closing a mass balance",
                "id": "POI-5025",
                "status": "To Research",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5025",
                "title": "Cursor researching: []Research: source of errors when closing a mass balance",
            },
        )

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Research issue",
                "id": "POI-5025",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "title": "Research issue",
            "id": "POI-5025",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "title": "cursor researching: Research issue",
            "id": "POI-5025",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5025",
                "title": "cursor researching: Research issue",
            },
        )

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "7e6baace-1b9c-40ad-a4f0-000000000000",
                    "identifier": "POI-5025",
                    "title": "Research issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5025",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5025",
                    "title": "Research issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_expected_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Research issue",
            "id": "POI-5025",
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
                "issueId": "POI-5025",
                "title": "Cursor researching: Research issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
