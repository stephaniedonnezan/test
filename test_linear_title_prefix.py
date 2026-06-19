import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4009",
            "title": "Add Select field on Delivery Form",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_prefixes_cursor_cloud_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4009",
                    "title": "Add Select field on Delivery Form",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4009",
            "title": "Add Select field on Delivery Form",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-4009",
            "title": "Add Select field on Delivery Form",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4009",
            "title": "cursor researching: Add Select field on Delivery Form",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-4009",
            "title": "Add Select field on Delivery Form",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4009",
                    "title": "Add Select field on Delivery Form",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_prioritizes_changed_status_over_stale_issue_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "linear-id",
                "identifier": "POI-4009",
                "title": "Add Select field on Delivery Form",
                "state": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4009",
                "title": "Add Select field on Delivery Form",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4009",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4009",
                "title": "Add Select field on Delivery Form",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )


if __name__ == "__main__":
    unittest.main()
