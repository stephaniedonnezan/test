import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5031",
                    "title": "Improve performance of timeZoneObject()",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5031",
                "title": "Cursor researching: Improve performance of timeZoneObject()",
            },
        )

    def test_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "status": "to_research",
            "issueId": "issue-1",
            "title": "Investigate slow query",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-1",
                "title": "Cursor researching: Investigate slow query",
            },
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "status": "QA Backend",
            "issueId": "issue-1",
            "title": "Investigate slow query",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_without_status_marker_is_ignored(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-1",
                "title": "Investigate slow query",
                "state": {"name": "To Research"},
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_linear_update_with_updated_from_state_id_is_prefixed(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "linear-id-1",
                "title": "Investigate slow query",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-id-1",
                "title": "Cursor researching: Investigate slow query",
            },
        )

    def test_updated_fields_list_status_marker_is_prefixed(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-1",
                "title": "Investigate slow query",
                "workflowState": {"name": "to research"},
            },
            "updatedFields": ["workflowState"],
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate slow query",
        )

    def test_object_shaped_changed_field_status_marker_is_prefixed(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-1",
                "title": "Investigate slow query",
                "status": {"name": "To Research"},
            },
            "changes": [{"field": "status", "from": "Backlog", "to": "To Research"}],
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate slow query",
        )

    def test_existing_prefix_is_ignored_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "issue-1",
            "title": "cursor researching: Investigate slow query",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_blank_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "issueId": "",
                    "title": "Investigate slow query",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "issueId": "issue-1",
                    "title": "   ",
                }
            )
        )

    def test_trims_issue_id_and_title_for_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " issue-1 ",
            "title": " Investigate slow query ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-1",
                "title": "Cursor researching: Investigate slow query",
            },
        )

    def test_cli_prints_json_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "issue-1",
            "title": "Investigate slow query",
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
                "issueId": "issue-1",
                "title": "Cursor researching: Investigate slow query",
            },
        )


if __name__ == "__main__":
    unittest.main()
