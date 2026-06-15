import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_status_changed_to_research_adds_cursor_researching_to_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4891",
                "title": "Update",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4891",
                "title": "Cursor researching: Update",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-4891",
                "title": "Update",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4891",
                "title": "Cursor researching: Update",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4891",
                "title": "Update",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4891",
                "title": "Update",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4891",
                "title": "cursor researching: Update",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4891",
                    "title": "Update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4891",
                "title": "Cursor researching: Update",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4891",
                    "title": "Update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_from_changes_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4891",
                    "title": "Update",
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4891",
                "title": "Cursor researching: Update",
            },
        )

    def test_cli_prints_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4891",
                "title": "Update",
            }
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
                "issueId": "POI-4891",
                "title": "Cursor researching: Update",
            },
        )


if __name__ == "__main__":
    unittest.main()
