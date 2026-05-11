import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_automation_research_status(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3681",
                "title": "15 minutes batching",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3681",
                "title": "Cursor researching: 15 minutes batching",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-1",
            "title": "Check edge case",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Check edge case",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2",
                "title": "Check edge case",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Check edge case",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": f"{TITLE_PREFIX}: Check edge case",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_updated_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5",
                "title": "Investigate report",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate report",
            },
        )

    def test_accepts_mapping_updated_fields_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Research workflow",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Research workflow",
            },
        )

    def test_ignores_issue_updated_payload_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Investigate report",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-7"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )

    def test_handler_alias_matches_primary_handler(self):
        event = {
            "trigger": "stateChanged",
            "status": "to research",
            "id": "POI-8",
            "title": "Check alias",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-9",
            "title": "Check CLI",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Check CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
