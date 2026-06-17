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
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4970",
                "title": "Changing from POS issuer role to User Role does not remove ability to close POSes",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4970",
                "title": (
                    "Cursor researching: Changing from POS issuer role to User Role "
                    "does not remove ability to close POSes"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4970",
                "title": "Bug title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Bug title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "cursor researching: Bug title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-1",
            "title": "Bug title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Bug title",
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "status": "To Research",
            "id": "POI-1",
            "title": "Bug title",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-1",
        )

    def test_generic_issue_update_ignores_non_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-1",
            "title": "Bug title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changed_status_metadata_wins_over_stale_issue_state(self):
        event = {
            "action": "update",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Bug title",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Bug title",
            },
        )

    def test_changed_fields_list_can_supply_new_status(self):
        event = {
            "action": "Issue Updated",
            "changedFields": [{"field": "workflowState", "newValue": "to_research"}],
            "issue": {
                "identifier": "POI-3",
                "title": "Bug title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Bug title",
        )

    def test_returns_none_without_issue_id_or_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Bug title",
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
                "issueId": "POI-4",
                "title": "Cursor researching: Bug title",
            },
        )


if __name__ == "__main__":
    unittest.main()
