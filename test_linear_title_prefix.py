import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_payload_adds_cursor_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4988",
                "title": "Cursor researching: Container production site can be added",
            },
        )

    def test_current_todo_status_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "Todo",
                "id": "POI-4988",
                "title": "Even though Container FF is deactivated",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_to_research_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Container production site can be added",
        )

    def test_existing_cursor_researching_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4988",
                "title": "cursor researching: Container production site can be added",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_prefers_linear_issue_id(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid-123",
                "identifier": "POI-4988",
                "title": "Container production site can be added",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid-123",
                "title": "Cursor researching: Container production site can be added",
            },
        )

    def test_generic_issue_update_without_status_change_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "linear-uuid-123",
                "title": "Container production site can be added",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_changes_map_can_supply_new_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "id": "linear-uuid-123",
                "title": "Container production site can be added",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Container production site can be added",
        )

    def test_missing_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4988",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Container production site can be added",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4988",
                "title": "Container production site can be added",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4988",
                "title": "Cursor researching: Container production site can be added",
            },
        )


if __name__ == "__main__":
    unittest.main()
