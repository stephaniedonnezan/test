import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_adds_prefix_for_cursor_trigger_context_shape(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_ignores_status_changed_event_for_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4800",
            "title": "cursor researching: MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_spelling_and_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4800",
                "title": "MB Grid Consumption zeros",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_supports_linear_updated_from_status_payloads(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"workflowState": {"name": "Todo"}},
            "data": {
                "id": "issue-id",
                "identifier": "POI-4800",
                "title": "MB Grid Consumption zeros",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_ignores_linear_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4800",
                "title": "MB Grid Consumption zeros",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4800",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "MB Grid Consumption zeros",
                }
            )
        )

    def test_cli_outputs_update_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        result = subprocess.run(
            [sys.executable, "-m", "linear_title_prefix"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
