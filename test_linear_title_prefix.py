import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4970",
                "title": "Changing from POS issuer role to User Role",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4970",
                "title": "Cursor researching: Changing from POS issuer role to User Role",
            },
        )

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate export bug",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export bug",
            },
        )

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-2",
                    "title": "Handle stale permissions",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Handle stale permissions",
            },
        )

    def test_prefers_changed_status_metadata_over_stale_issue_state(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Refresh roles",
                    "state": {"name": "Todo"},
                },
                "changes": {
                    "workflowState": {
                        "oldValue": {"name": "Todo"},
                        "newValue": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Refresh roles",
            },
        )

    def test_ignores_generic_issue_update_without_changed_status_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-4",
                    "title": "Rename only",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "issueId": "POI-5",
            "title": "No action",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "issueId": "POI-6",
            "title": "Comment should not change title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-7",
            "title": "Cursor researching: Existing title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Existing title",
            },
        )

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-8",
            "title": "cursor researching - Existing title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "cursor researching - Existing title",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "issueId": "POI-9"}
            )
        )

    def test_cli_prints_action_for_matching_event(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-10",
            "title": "CLI title",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
