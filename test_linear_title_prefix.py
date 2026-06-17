import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_updates_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4977",
                "title": "Auditor can access Producer page",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": "Cursor researching: Auditor can access Producer page",
            },
        )

    def test_normalizes_case_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "issueId": "POI-4977",
            "title": "Research direct URL access",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research direct URL access",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4977",
            "title": "Auditor can access Producer page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_even_if_current_status_is_research(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4977",
            "title": "Auditor can access Producer page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4977",
            "title": "cursor researching: Auditor can access Producer page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_with_state_field(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "wrapper-id",
                "issue": {
                    "identifier": "POI-4977",
                    "title": "Auditor can access Producer page",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": "Cursor researching: Auditor can access Producer page",
            },
        )

    def test_generic_update_can_read_changed_status_to_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": {"name": "to research"}}},
            "key": "POI-4977",
            "title": "Auditor can access Producer page",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Auditor can access Producer page",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to research",
            "id": " POI-4977 ",
            "title": "  Auditor can access Producer page  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": "Cursor researching: Auditor can access Producer page",
            },
        )

    def test_missing_issue_id_or_title_returns_none(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing ID"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4977"}
            )
        )

    def test_non_mapping_payload_returns_none(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_from_stdin_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4977",
                "title": "Auditor can access Producer page",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": "Cursor researching: Auditor can access Producer page",
            },
        )


if __name__ == "__main__":
    unittest.main()
