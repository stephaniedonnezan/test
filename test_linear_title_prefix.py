import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_accepts_nested_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_accepts_linear_issue_update_when_state_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_accepts_status_value_from_changes(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "data": {
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
            },
            "changes": {"status": {"from": "Backlog", "to": "to_research"}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Optimize offtaker fifo allocation",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "cursor researching: Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4930",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Optimize offtaker fifo allocation",
                }
            )
        )

    def test_cli_prints_computed_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
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
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
