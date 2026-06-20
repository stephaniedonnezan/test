import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_cloud_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4826",
                    "title": "Update container allocation data",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: Update container allocation data",
            },
        )

    def test_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To Research",
            "issueId": "POI-1234",
            "title": "Investigate allocations",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate allocations",
        )

    def test_accepts_separator_variants_for_target_status(self):
        event = {
            "trigger": "workflowStateChanged",
            "newStatus": "to_research",
            "identifier": "POI-2345",
            "title": "Research status formatting",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-2345",
        )

    def test_nested_linear_issue_update_uses_change_destination_status(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-3456",
                    "title": "Nested Linear update",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3456",
                "title": "Cursor researching: Nested Linear update",
            },
        )

    def test_nested_change_list_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": [
                {
                    "field": "workflowState",
                    "newValue": {"name": "To Research"},
                }
            ],
            "data": {
                "id": "issue-1",
                "issue": {
                    "id": "POI-4567",
                    "title": "List changes",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: List changes",
        )

    def test_uses_status_fallback_when_new_status_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-5678",
            "title": "Fallback status",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5678",
        )

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-6789",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-7890",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8901",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "  POI-9012  ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9012",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_returns_none_for_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-0123",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4826",
            "title": "CLI smoke test",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4826",
                "title": "Cursor researching: CLI smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
