import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3171",
            "title": '"undo" document upload',
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3171",
                "title": 'Cursor researching: "undo" document upload',
            },
        )

    def test_prefixes_automation_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Add search indexing",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Add search indexing",
            },
        )

    def test_accepts_status_case_separator_and_camel_case_variants(self):
        events = [
            {"trigger": "statusChanged", "new_status": "to_research"},
            {"trigger": "state_changed", "newState": "toResearch"},
            {"trigger": "workflow_state_changed", "toStatus": "TO RESEARCH"},
        ]

        for index, event in enumerate(events, start=1):
            with self.subTest(event=event):
                event.update({"issueId": f"POI-{index}", "title": "Normalize status"})
                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Normalize status",
                )

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-456",
                "title": "Audit permissions",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Audit permissions",
            },
        )

    def test_prefixes_updated_from_status_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "Issue Updated",
            "updatedFrom": {"workflowStateId": "old-state-id"},
            "data": {
                "id": "POI-789",
                "title": "Evaluate rate limits",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Evaluate rate limits",
            },
        )

    def test_prioritizes_explicit_new_status_over_stale_nested_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issue": {
                "id": "POI-321",
                "title": "Explicit status wins",
                "status": "In Progress",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Explicit status wins",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-3171",
            "title": '"undo" document upload',
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3171",
            "title": '"undo" document upload',
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_linear_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-456",
                "title": "Audit permissions",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3171",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["state"],
                    "data": {"id": "POI-999", "state": {"name": "To Research"}},
                }
            )
        )
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-101",
            "title": "Scope task",
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
                "issueId": "POI-101",
                "title": "Cursor researching: Scope task",
            },
        )

    def test_cli_rejects_invalid_json(self):
        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input="{invalid",
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
