import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_cloud_automation_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4152",
                    "title": "Add ID field for supply contracts",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4152",
                "title": "Cursor researching: Add ID field for supply contracts",
            },
        )

    def test_flat_trigger_context_status_changed(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-100",
                "title": "Investigate storage loss",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Investigate storage loss",
            },
        )

    def test_nested_linear_update_prefers_identifier_over_webhook_id(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "id": "webhook-event-id",
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-101",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_linear_changes_to_status_name(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-102",
                "title": "Changed through workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-102",
                "title": "Cursor researching: Changed through workflow state",
            },
        )

    def test_accepts_camel_case_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issue_id": "POI-103",
            "title": "Camel status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-103",
                "title": "Cursor researching: Camel status",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-104",
            "title": "No explicit new status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-104",
                "title": "Cursor researching: No explicit new status",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-105",
            "title": "Completed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "identifier": "POI-106",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-107",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "  POI-108  ",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-108",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_returns_none_for_missing_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-109",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-110",
            "title": "CLI issue",
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
                "issueId": "POI-110",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
