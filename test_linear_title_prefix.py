import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5045",
                    "title": '[]Supply contract only states "producer"',
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": 'Cursor researching: []Supply contract only states "producer"',
            },
        )

    def test_flat_trigger_context_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "issueId": "POI-1",
                "title": "Trader contract copy",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Trader contract copy",
            },
        )

    def test_normalizes_status_separators_and_case(self):
        event = {
            "trigger": "stateChanged",
            "new_status": "TO_RESEARCH",
            "identifier": "POI-2",
            "title": "Asset address label",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Asset address label",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-3",
            "title": "Asset type label",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "Yearly amount optional",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-6"}
            )
        )

    def test_nested_linear_update_with_changed_state_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-7",
                    "title": "Supply contract labels",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Supply contract labels",
            },
        )

    def test_nested_linear_change_value_takes_precedence_over_stale_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": {"name": "Todo"}, "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-8",
                "title": "Explicit change status",
                "state": {"name": "In Progress"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Explicit change status",
            },
        )

    def test_generic_update_ignores_non_status_field_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-9",
                "title": "Description edit",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
            "title": "CLI smoke",
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
                "issueId": "POI-10",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
