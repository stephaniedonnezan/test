import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4896",
                "title": "Cool refactor to push straight to main - `SiteFrame`",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4896",
                "title": "Cursor researching: Cool refactor to push straight to main - `SiteFrame`",
            },
        )

    def test_normalizes_trigger_and_status_text(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-100",
            "title": "Normalize this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Normalize this",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-101",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-102",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-103",
            "title": "cursor researching: Already handled",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-104",
                "title": "Nested payload",
                "state": {"name": "To Research"},
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-104",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_nested_issue_object_with_workflow_state(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-105",
                    "title": "Workflow state payload",
                    "workflowState": {"name": "To Research"},
                },
                "updatedFields": [{"name": "workflowState"}],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-105",
                "title": "Cursor researching: Workflow state payload",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-106",
                "title": "Changes payload",
                "changes": {
                    "status": {
                        "from": "Todo",
                        "to": "To Research",
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-106",
                "title": "Cursor researching: Changes payload",
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-107",
                "title": "Title-only payload",
                "state": {"name": "To Research"},
                "updatedFields": ["title"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_title_or_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-108"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "No ID"})
        )

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-109",
                "title": "CLI payload",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-109",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
