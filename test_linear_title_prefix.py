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
                "id": "POI-4985",
                "title": "Offtaker form field is confusing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4985",
                "title": "Offtaker form field is confusing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4985",
                "title": "Offtaker form field is confusing",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4985",
            "title": "cursor researching: Offtaker form field is confusing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_with_separator_and_case_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-4985",
            "title": "Offtaker form field is confusing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )

    def test_accepts_generic_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "status"],
            "status": "to research",
            "identifier": "POI-4985",
            "title": "Offtaker form field is confusing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "identifier": "POI-4985",
            "title": "Offtaker form field is confusing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4985",
                    "title": "Offtaker form field is confusing",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFrom": {"state": {"name": "Inbox"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )

    def test_accepts_changed_status_value(self):
        event = {
            "action": "issue_updated",
            "changes": {"state": {"oldValue": "Backlog", "newValue": "to research"}},
            "identifier": "POI-4985",
            "title": "Offtaker form field is confusing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Offtaker form field is confusing",
        }

        self.assertIsNone(build_issue_title_update(event))


class CliTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4985",
            "title": "Offtaker form field is confusing",
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
                "issueId": "POI-4985",
                "title": "Cursor researching: Offtaker form field is confusing",
            },
        )


if __name__ == "__main__":
    unittest.main()
