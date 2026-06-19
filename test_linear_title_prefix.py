import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3611",
                "title": "Add a Container Delivery Emission Strategy handler Strategy",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3611",
                "title": (
                    "Cursor researching: "
                    "Add a Container Delivery Emission Strategy handler Strategy"
                ),
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-3611",
                "title": "Add title prefix automation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-3611",
                    "title": "Add title prefix automation",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "issueId": "POI-3611",
                "title": "cursor researching: Add title prefix automation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "TO_RESEARCH",
                "issue_id": "POI-3611",
                "title": "Add title prefix automation",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: Add title prefix automation")

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3611",
                    "title": "Add title prefix automation",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3611",
                "title": "Cursor researching: Add title prefix automation",
            },
        )

    def test_prefers_changed_status_value_over_current_issue_state(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-3611",
                    "title": "Add title prefix automation",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3611",
                "title": "Cursor researching: Add title prefix automation",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3611",
                "title": "Add title prefix automation",
            }
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
                "issueId": "POI-3611",
                "title": "Cursor researching: Add title prefix automation",
            },
        )


if __name__ == "__main__":
    unittest.main()
