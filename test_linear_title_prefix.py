import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4884",
            "title": "lock qualified outputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: lock qualified outputs",
            },
        )

    def test_prefixes_cloud_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4884",
                "title": "lock qualified outputs",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: lock qualified outputs",
            },
        )

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4884",
                    "title": "lock qualified outputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: lock qualified outputs",
            },
        )

    def test_prefers_new_status_over_existing_issue_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["status"],
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "identifier": "POI-4884",
                    "title": "lock qualified outputs",
                    "status": {"name": "Backlog"},
                }
            },
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"workflowState": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4884",
                    "title": "lock qualified outputs",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: lock qualified outputs",
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-4884",
            "title": "lock qualified outputs",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4884",
            "title": "lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_create_events_even_with_research_status(self):
        event = {
            "action": "create",
            "type": "Issue",
            "updatedFields": ["status"],
            "status": "To Research",
            "identifier": "POI-4884",
            "title": "lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "cursor researching: lock qualified outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4884"}

        self.assertIsNone(build_issue_title_update(event))

    def test_main_prints_update_action_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4884",
            "title": "lock qualified outputs",
        }

        with patch("sys.stdin", io.StringIO(json.dumps(event))):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: lock qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
