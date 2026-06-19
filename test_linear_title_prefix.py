import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4964",
                "title": "Cursor researching: Invite link not showing after user is invited",
            },
        )

    def test_accepts_cloud_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4964",
                "title": "Invite link not showing after user is invited",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4964",
                "title": "Cursor researching: Invite link not showing after user is invited",
            },
        )

    def test_accepts_cloud_automation_trigger_info_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4964",
                    "title": "Invite link not showing after user is invited",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4964",
                "title": "Cursor researching: Invite link not showing after user is invited",
            },
        )

    def test_accepts_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Research status title update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research status title update",
            },
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "issue": {
                "identifier": "POI-456",
                "title": "Workflow state change payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Workflow state change payload",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Backlog",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_with_new_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-4964",
            "title": "cursor researching: Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-789",
            "title": "Camel case payload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Camel case payload",
            },
        )

    def test_requires_issue_identifier_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4964",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
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
                "issueId": "POI-4964",
                "title": "Cursor researching: Invite link not showing after user is invited",
            },
        )


if __name__ == "__main__":
    unittest.main()
