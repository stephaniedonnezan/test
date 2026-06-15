import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )

    def test_accepts_direct_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-123",
            "title": "Investigate importer",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate importer",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "to research",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4885",
            "title": "cursor researching: unlock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_target_status_separators_and_case(self):
        event = {
            "trigger": "status_changed",
            "new_status": "To-Research",
            "identifier": "POI-4885",
            "title": "unlock qualified outputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )

    def test_supports_nested_linear_updated_state_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4885",
                    "title": "unlock qualified outputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )

    def test_uses_change_destination_status(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-4885",
                "title": "unlock qualified outputs",
                "state": {"name": "Backlog"},
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
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4885",
                "title": "unlock qualified outputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "unlock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4885",
                "title": "unlock qualified outputs",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4885",
                "title": "Cursor researching: unlock qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
