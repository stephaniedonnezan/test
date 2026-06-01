import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_trigger(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4640",
            "title": "Fix delivery trip saving",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: Fix delivery trip saving",
            },
        )

    def test_builds_update_from_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4640",
                "title": "Transaction saves all trips",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: Transaction saves all trips",
            },
        )

    def test_ignores_statuses_other_than_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4640",
            "title": "Fix delivery trip saving",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4640",
            "title": "Fix delivery trip saving",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4640",
            "title": "cursor researching: Fix delivery trip saving",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "trigger": "status changed",
            "new_status": "TO_RESEARCH",
            "issue_id": "POI-4640",
            "title": " Fix delivery trip saving ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: Fix delivery trip saving",
            },
        )

    def test_builds_update_from_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_builds_update_from_nested_trigger_context_issue(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "data": {
                    "issue": {
                        "identifier": "POI-4640",
                        "title": "Nested trigger issue",
                        "status": "to-research",
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: Nested trigger issue",
            },
        )

    def test_supports_workflow_state_fallback(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": [{"field": "workflowState"}],
            "issue": {
                "id": "POI-4640",
                "title": "Workflow state issue",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: Workflow state issue",
            },
        )

    def test_ignores_invalid_or_incomplete_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4640"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4640",
            "title": "CLI issue",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4640",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
