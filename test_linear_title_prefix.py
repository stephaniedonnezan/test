import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4036",
            "title": "Disable the Close Button in individual sites",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4036",
                "title": "Cursor researching: Disable the Close Button in individual sites",
            },
        )

    def test_builds_update_for_cloud_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-4036",
                    "title": "Research status title prefix",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4036",
                "title": "Cursor researching: Research status title prefix",
            },
        )

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-123",
                "title": "Nested issue payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_builds_update_from_changed_status_payload(self):
        event = {
            "type": "Issue Updated",
            "data": {"identifier": "POI-321", "title": "Changed status payload"},
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Changed status payload",
            },
        )

    def test_normalizes_camel_case_research_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-456",
            "title": "Camel case status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case status",
        )

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4036",
            "title": "Disable the Close Button in individual sites",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-123",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_is_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-789",
            "title": "CLI event",
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
                "issueId": "POI-789",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
