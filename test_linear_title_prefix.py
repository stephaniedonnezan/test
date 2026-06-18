import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4871",
                "title": "Container allocation search field",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4871",
                "title": "Cursor researching: Container allocation search field",
            },
        )

    def test_accepts_camel_case_status_names(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4871",
            "title": "Inspect allocation canvas",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Inspect allocation canvas",
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4871",
            "title": "Inspect allocation canvas",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4871",
            "title": "Inspect allocation canvas",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-4871",
            "title": "cursor researching: Inspect allocation canvas",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "26fca9db",
                "identifier": "POI-4871",
                "title": "Inspect allocation canvas",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4871",
                "title": "Cursor researching: Inspect allocation canvas",
            },
        )

    def test_uses_changed_status_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "identifier": "POI-4871",
                "title": "Inspect allocation canvas",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Inspect allocation canvas",
        )

    def test_ignores_update_events_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4871",
                "title": "Inspect allocation canvas",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4871",
            "title": "Inspect allocation canvas",
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
                "issueId": "POI-4871",
                "title": "Cursor researching: Inspect allocation canvas",
            },
        )


if __name__ == "__main__":
    unittest.main()
