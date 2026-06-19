import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )

    def test_normalizes_research_status_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-1",
                "title": "Research status variant",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research status variant",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-2",
                "title": "Comment update",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "cursor researching: Existing prefix",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_updated_from_state(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "linear-internal-id",
                "identifier": "POI-4",
                "title": "Nested Linear payload",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"state": {"name": "Todo"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_generic_issue_update_requires_status_field_marker(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "identifier": "POI-5",
                "title": "Description-only update",
                "state": {"name": "To Research"},
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_updated_fields_can_mark_status_change(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "identifier": "POI-6",
                "title": "Updated fields payload",
                "workflowState": {"name": "To Research"},
            },
            "updatedFields": ["workflowState"],
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Updated fields payload",
        )

    def test_changes_metadata_can_supply_new_status(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "identifier": "POI-7",
                "title": "Changes payload",
            },
            "changes": {
                "state": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changes payload",
        )

    def test_missing_issue_id_or_title_returns_none(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-8",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-9",
                "title": "CLI payload",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
