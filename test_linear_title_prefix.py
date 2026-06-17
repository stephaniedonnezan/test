import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5038",
            "title": "Suppliers and Supply Contracts need to converge on the same name",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5038",
                "title": (
                    "Cursor researching: "
                    "Suppliers and Supply Contracts need to converge on the same name"
                ),
            },
        )

    def test_reads_automation_trigger_context_before_outer_fields(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5038",
                "title": "Issue title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5038",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_RESEARCH",
            "issueId": "POI-1",
            "title": "Case variants",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Case variants",
            },
        )

    def test_accepts_nested_linear_update_with_updated_from_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-2",
                "title": "Nested webhook",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested webhook",
            },
        )

    def test_accepts_generic_issue_update_with_changed_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title", "status"],
            "issue_id": "POI-3",
            "title": "Changed status field",
            "status": "to-research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Changed status field",
            },
        )

    def test_ignores_non_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5038",
            "title": "Current trigger title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "POI-5",
                "title": "Title edit",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"title": "Old title"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
                }
            )
        )

    def test_cli_prints_json_action(self):
        stdin = io.StringIO(
            json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-8",
                    "title": "CLI payload",
                }
            )
        )
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
