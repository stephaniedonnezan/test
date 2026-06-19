import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_cloud_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4166",
                "title": "Preview upload network error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4166",
                "title": "Cursor researching: Preview upload network error",
            },
        )

    def test_returns_update_for_automation_trigger_info_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4166",
                    "title": "Transport emissions validation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4166",
                "title": "Cursor researching: Transport emissions validation",
            },
        )

    def test_normalizes_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-1",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4166",
                "title": "Preview upload network error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-2",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_are_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-3",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_update_for_linear_issue_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_returns_update_for_status_changes_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "to research"}},
            "issue": {"key": "POI-5", "title": "Changes payload"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changes payload",
        )

    def test_ignores_issue_updates_without_status_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "issueId": "POI-6",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-7",
            "title": "CLI event",
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
