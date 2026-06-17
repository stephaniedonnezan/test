import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4989",
            "title": "0 stays in Site creation Dialogue despite adding a number",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": (
                    "Cursor researching: "
                    "0 stays in Site creation Dialogue despite adding a number"
                ),
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4989",
                "title": "Investigate site creation dialog",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "Cursor researching: Investigate site creation dialog",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-1234",
                    "title": "Nested payload title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Nested payload title",
            },
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "data": {"issue": {"id": "issue-id", "title": "Changed by workflow state"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Changed by workflow state",
            },
        )

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-9999",
            "title": "Normalize names",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9999",
                "title": "Cursor researching: Normalize names",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4989",
            "title": "cursor researching: Existing work",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "cursor researching: Existing work",
            },
        )

    def test_ignores_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4989",
            "title": "Still todo",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4989",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4989",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4989",
                "title": "CLI title",
            }
        }
        output = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(output):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
