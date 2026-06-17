import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_cursor_status_change_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3943",
            "title": "Feedstock-to-Nabisy-Biomasse-Code lookup table",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3943",
                "title": "Cursor researching: Feedstock-to-Nabisy-Biomasse-Code lookup table",
            },
        )

    def test_whole_cursor_automation_payload_uses_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4000",
                "title": "Review ISCC parser",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4000",
                "title": "Cursor researching: Review ISCC parser",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "  TO_research  ",
            "issueId": "POI-1",
            "title": "Parser",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Parser",
            },
        )

    def test_non_target_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-3943",
            "title": "Feedstock-to-Nabisy-Biomasse-Code lookup table",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_update_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "status": "To Research",
            "id": "POI-2",
            "title": "Priority-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_state_update_adds_prefix(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-4",
                "title": "Nested Linear payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_nested_issue_payload_is_supported(self):
        event = {
            "webhookType": "issue",
            "action": "update",
            "updatedFields": [{"field": "workflowState"}],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested issue object",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested issue object",
            },
        )

    def test_status_from_changes_adds_prefix(self):
        event = {
            "action": "update",
            "changes": {"state": {"newValue": {"name": "To Research"}}},
            "issue": {
                "id": "POI-6",
                "title": "Changed state object",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed state object",
            },
        )

    def test_title_and_issue_id_are_trimmed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "issue_id": "  POI-7  ",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_missing_issue_identity_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "CLI payload",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
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
