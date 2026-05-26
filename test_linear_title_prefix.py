import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3154",
            "title": "[Refactoring] Document Upload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3154",
                "title": "Cursor researching: [Refactoring] Document Upload",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "Investigate traceability flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate traceability flow",
            },
        )

    def test_accepts_nested_automation_trigger_info_payload(self):
        event = {
            "automation_trigger_info": {
                "automationId": "automation-id",
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to research",
                    "id": "POI-456",
                    "title": "Model monthly inventory",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Model monthly inventory",
            },
        )

    def test_accepts_nested_linear_update_payload_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "identifier": "POI-789",
                    "title": "Handle green CO2 stock",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Handle green CO2 stock",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-101",
            "title": "Handle traceability exports",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Handle traceability exports",
            },
        )

    def test_accepts_linear_updated_from_status_field(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Check research transition",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Check research transition",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-3154",
            "title": "[Refactoring] Document Upload",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-3154",
            "title": "[Refactoring] Document Upload",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_payload_when_non_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "data": {
                "issue": {
                    "id": "POI-3154",
                    "title": "[Refactoring] Document Upload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3154",
            "title": "cursor researching: [Refactoring] Document Upload",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Missing ID"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-3154"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3154",
            "title": "[Refactoring] Document Upload",
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
                "issueId": "POI-3154",
                "title": "Cursor researching: [Refactoring] Document Upload",
            },
        )


if __name__ == "__main__":
    unittest.main()
