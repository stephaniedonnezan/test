import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4790",
            "title": "Rename co2 excel export columns (and reorder)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4790",
                "title": "Cursor researching: Rename co2 excel export columns (and reorder)",
            },
        )

    def test_accepts_cloud_automation_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Research inventory edge cases",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research inventory edge cases",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-456",
                "id": "0ef0d3d6-86f8-45e4-bc70-592f9c016b76",
                "title": "Map supplier data",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Map supplier data",
            },
        )

    def test_prefers_linear_identifier_over_uuid_id(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "ToResearch",
            "id": "0ef0d3d6-86f8-45e4-bc70-592f9c016b76",
            "identifier": "POI-789",
            "title": "Collect methane notes",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-789")

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "trigger": "status-changed",
            "new_status": "to_research",
            "issueId": "POI-321",
            "title": "Normalize payload values",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize payload values",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-654",
            "title": "cursor researching: Already marked",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Already marked",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "issueId": "POI-111",
            "title": "Ship the feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_event(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "issueId": "POI-222",
            "title": "A title edit should not trigger",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_from_changes_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "data": {
                "identifier": "POI-333",
                "title": "Inspect reports",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-333",
                "title": "Cursor researching: Inspect reports",
            },
        )

    def test_ignores_missing_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "issueId": "POI-444"}
            )
        )


class CliTests(unittest.TestCase):
    def test_main_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-555",
            "title": "CLI smoke test",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-555",
                "title": "Cursor researching: CLI smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
