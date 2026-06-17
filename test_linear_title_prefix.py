import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4886",
                "title": "get qualified outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4886",
                "title": "Cursor researching: get qualified outputs",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4886",
                "title": "get qualified outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4886",
                "title": "get qualified outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4886",
                "title": "cursor researching: get qualified outputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4886",
                "title": "get qualified outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4886",
                "title": "Cursor researching: get qualified outputs",
            },
        )

    def test_handles_nested_linear_update_with_changed_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-4886",
                    "title": "get qualified outputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4886",
                "title": "Cursor researching: get qualified outputs",
            },
        )

    def test_prefers_changed_destination_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": {"name": "Backlog"}, "to": {"name": "to_research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4886",
                    "title": "get qualified outputs",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4886",
                "title": "Cursor researching: get qualified outputs",
            },
        )

    def test_ignores_generic_update_without_status_changed_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4886",
                    "title": "get qualified outputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4886",
                "title": "get qualified outputs",
            }
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
                "issueId": "POI-4886",
                "title": "Cursor researching: get qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
