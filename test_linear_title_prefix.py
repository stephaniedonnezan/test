import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_context(self):
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

    def test_builds_update_for_cloud_automation_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4930",
                    "title": "Optimize offtaker fifo allocation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_linear_issue_update_with_state_change(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "POI-4930",
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

    def test_reads_new_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": {"name": "to-research"}}},
            "data": {
                "identifier": "POI-4930",
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

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To_Research",
            "issueId": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Optimize offtaker fifo allocation",
        )

    def test_skips_titles_that_already_have_prefix(self):
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

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))

    def test_cli_prints_matching_update(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            main()

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
