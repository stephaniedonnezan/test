import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_cursor_status_change_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4146",
                "title": "Export improvements",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4146",
                "title": "Cursor researching: Export improvements",
            },
        )

    def test_accepts_normalized_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "Clarify mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Clarify mass balance",
            },
        )

    def test_handles_linear_update_payload_with_updated_from(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-456",
                "title": "Research delivery export",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Research delivery export",
            },
        )

    def test_prefers_nested_issue_metadata_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Review export automation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review export automation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4146",
                "title": "Export improvements",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "issueId": "POI-123",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_old_status_values_from_updated_from(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "issue-uuid",
                "title": "Issue moved elsewhere",
                "state": {"name": "In Review"},
            },
            "updatedFrom": {"state": {"name": "To Research"}},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-123",
            "title": "CLI title",
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
                "issueId": "POI-123",
                "title": "Cursor researching: CLI title",
            },
        )

    def test_cli_prints_null_for_non_matching_payloads(self):
        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps({"trigger": "status_changed", "newStatus": "Done"}),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "null")


if __name__ == "__main__":
    unittest.main()
