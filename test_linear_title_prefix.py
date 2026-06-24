import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3977",
                "title": "Write backend tests to make sure POSes are correct",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3977",
                "title": "Cursor researching: Write backend tests to make sure POSes are correct",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3977",
                "title": "Write backend tests to make sure POSes are correct",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3977",
                "title": "Write backend tests to make sure POSes are correct",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3977",
                "title": "cursor researching: Write backend tests",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-3977",
                "title": "Write backend tests",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3977",
                "title": "Cursor researching: Write backend tests",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3977",
                    "title": "Write backend tests",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3977",
                "title": "Cursor researching: Write backend tests",
            },
        )

    def test_requires_status_field_for_generic_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["assignee"],
            "data": {
                "issue": {
                    "identifier": "POI-3977",
                    "title": "Write backend tests",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3977",
                "title": "Write backend tests",
            }
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
                "issueId": "POI-3977",
                "title": "Cursor researching: Write backend tests",
            },
        )


if __name__ == "__main__":
    unittest.main()
