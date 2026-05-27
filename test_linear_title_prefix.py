import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_updates_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_cursor_trigger_context_payload_updates_title(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4751",
            "title": "cursor researching: Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_separator_variants_for_target_status(self):
        event = {
            "trigger": "status-changed",
            "new_status": "to_research",
            "issue_id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Knowledge support on a POS-related question",
        )

    def test_accepts_linear_update_when_updated_fields_include_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4751",
                "title": "Knowledge support on a POS-related question",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_ignores_linear_update_when_updated_fields_do_not_include_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4751",
                "title": "Knowledge support on a POS-related question",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changes_map_with_workflow_state(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"old": "Todo", "new": "To Research"}},
            "id": "issue-uuid",
            "title": "Knowledge support on a POS-related question",
            "workflowState": {"name": "To Research"},
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "issue-uuid",
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4751 ",
            "title": "  Knowledge support on a POS-related question  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )


if __name__ == "__main__":
    unittest.main()
