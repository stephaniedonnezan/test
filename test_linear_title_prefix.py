import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_event_for_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4952",
                "title": "Cost monitoring & abuse protection",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4952",
                "title": "Cursor researching: Cost monitoring & abuse protection",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4952",
                "title": "Cost monitoring & abuse protection",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "issue_commented",
                "newStatus": "to research",
                "id": "POI-4952",
                "title": "Cost monitoring & abuse protection",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4952",
                "title": "cursor researching: Cost monitoring & abuse protection",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4952",
                "title": "cursor researching: Cost monitoring & abuse protection",
            },
        )

    def test_handles_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4952",
                    "title": "Cost monitoring & abuse protection",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4952",
                "title": "Cursor researching: Cost monitoring & abuse protection",
            },
        )

    def test_ignores_nested_linear_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4952",
                    "title": "Cost monitoring & abuse protection",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to-research",
                "id": "POI-4952",
                "title": "Cost monitoring & abuse protection",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            encoding="utf-8",
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4952",
                "title": "Cursor researching: Cost monitoring & abuse protection",
            },
        )


if __name__ == "__main__":
    unittest.main()
