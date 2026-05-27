import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4705",
            "title": "[Backend] WRT orchestration",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4705",
                "title": "Cursor researching: [Backend] WRT orchestration",
            },
        )

    def test_accepts_cursor_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate route calculation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate route calculation",
            },
        )

    def test_accepts_nested_linear_issue_update_with_changed_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-321",
                "title": "Research optimizer edge cases",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research optimizer edge cases",
            },
        )

    def test_accepts_linear_changes_payload_for_status_update(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                },
            },
            "data": {
                "issue": {
                    "id": "issue-with-changes",
                    "title": "Evaluate WRT orchestration",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-with-changes",
                "title": "Cursor researching: Evaluate WRT orchestration",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4705",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4705",
                "title": "Do not update",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-4705",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4705",
            "title": "CLI title",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4705",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
