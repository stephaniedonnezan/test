import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5043",
                "title": "Add address autofill to offtaker creation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5043",
                "title": "Cursor researching: Add address autofill to offtaker creation",
            },
        )

    def test_current_non_target_status_is_ignored(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5043",
                "title": "We use an address fetcher with auto fill in other views",
                "status": "In Progress",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_and_trigger_normalization_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "TO_RESEARCH",
                "issueId": "POI-100",
                "title": "Normalize status names",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Normalize status names",
            },
        )

    def test_already_prefixed_title_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-101",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-102",
                "title": "Comment changed only",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-103",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-103",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-104",
                    "title": "Description-only change",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_map_destination_status_is_supported(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": {"name": "Backlog"}, "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-105",
                "title": "Changes map issue",
                "workflowState": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-105",
                "title": "Cursor researching: Changes map issue",
            },
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "No issue id",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-106",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-107",
                "title": "CLI issue",
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
                "issueId": "POI-107",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
