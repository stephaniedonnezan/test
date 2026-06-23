import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4934",
            "title": "Issues panel must be visible across all tabs in container view",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs in container view",
            },
        )

    def test_supports_cloud_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4934",
                "title": "Wrapped payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Wrapped payload",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-internal-id",
                    "identifier": "POI-4934",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_prefers_changed_status_value_over_current_issue_status(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "changes": {
                "workflowState": {
                    "oldValue": "Backlog",
                    "newValue": "to_research",
                },
            },
            "data": {
                "issue": {
                    "identifier": "POI-4934",
                    "title": "Change payload",
                    "workflowState": {"name": "Backlog"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Change payload",
            },
        )

    def test_supports_change_list_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": [
                {
                    "field": "status",
                    "from": "Todo",
                    "to": {"name": "To Research"},
                }
            ],
            "data": {
                "issue": {
                    "identifier": "POI-4934",
                    "title": "List change payload",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: List change payload",
            },
        )

    def test_ignores_non_status_update_with_new_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-4934",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4934",
            "title": "Completed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_unrelated_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4934",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-4934",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4934",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4934",
            "title": "CLI payload",
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
                "issueId": "POI-4934",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
