import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3139",
                "title": "Monitor API Key activity and react to IP changes",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3139",
                "title": "Cursor researching: Monitor API Key activity and react to IP changes",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-3139",
                "title": "Monitor API Key activity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3139",
                "title": "Monitor API Key activity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3139",
                "title": "cursor researching: Monitor API Key activity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-3139",
                "title": "Monitor API Key activity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Monitor API Key activity",
        )

    def test_accepts_nested_linear_update_with_state_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Monitor API Key activity",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Monitor API Key activity",
            },
        )

    def test_ignores_linear_update_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Monitor API Key activity",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_workflow_state_name_fallback(self):
        event = {
            "type": "Updated Issue",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "POI-3139",
                "title": "Monitor API Key activity",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-3139",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3139",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3139",
                "title": "Monitor API Key activity",
            }
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
                "issueId": "POI-3139",
                "title": "Cursor researching: Monitor API Key activity",
            },
        )


if __name__ == "__main__":
    unittest.main()
