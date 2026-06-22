import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_accepts_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1",
            "title": "Investigate supplier inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate supplier inputs",
            },
        )

    def test_accepts_generic_issue_update_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "new_status": "to_research",
            "identifier": "POI-2",
            "title": "Research registry evidence",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research registry evidence",
            },
        )

    def test_accepts_nested_linear_webhook_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-3",
                "title": "Review e-methane calculation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Review e-methane calculation",
            },
        )

    def test_accepts_status_from_changes_new_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "key": "POI-4",
            "title": "Confirm CO2 contract rules",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Confirm CO2 contract rules",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5",
            "title": "Do implementation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-6",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-8"}
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "CLI title",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
