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
                "id": "POI-4325",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4325",
                "title": "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
            },
        )

    def test_cloud_automation_payload_adds_cursor_researching_prefix(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4325",
                    "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4325",
                "title": "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
            },
        )

    def test_current_todo_status_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "Todo",
                "id": "POI-4325",
                "title": "Even though Container FF is deactivated",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4325",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_to_research_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4325",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
        )

    def test_existing_cursor_researching_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4325",
                "title": "cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
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
                "identifier": "POI-4325",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid-123",
                "title": "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
            },
        )

    def test_generic_issue_update_without_status_change_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "linear-uuid-123",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
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
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
        )

    def test_missing_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4325",
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
                        "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4325",
                "title": "Hide Storage Loss card when there is no loss recorded instead of N/A",
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
                "issueId": "POI-4325",
                "title": "Cursor researching: Hide Storage Loss card when there is no loss recorded instead of N/A",
            },
        )


if __name__ == "__main__":
    unittest.main()
