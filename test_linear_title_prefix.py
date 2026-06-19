import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import PREFIX, build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4665",
            "title": "Make a unit test for all required fields",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4665",
                "title": "Cursor researching: Make a unit test for all required fields",
            },
        )

    def test_builds_update_for_nested_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "Research title automation",
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-123")
        self.assertEqual(update["title"], "Cursor researching: Research title automation")

    def test_accepts_status_changed_camel_case_and_snake_case_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-234",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_accepts_linear_issue_update_when_updated_fields_include_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-345",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-345")
        self.assertEqual(update["title"], "Cursor researching: Nested Linear payload")

    def test_prefers_changed_status_over_stale_nested_issue_status(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "POI-456",
                    "title": "Changed status payload",
                    "workflowState": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status payload",
        )

    def test_returns_none_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-567",
            "title": "Completed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-678",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-789",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-890",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-901",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-902",
            "title": "CLI payload",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-902",
                "title": f"{PREFIX}: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
