import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5056",
            "title": "Research a flaky close error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-5056",
            "title": "2026-06-18-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5056",
            "title": "Research a flaky close error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5056",
            "title": "cursor researching: Research a flaky close error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_normalized_status_and_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "identifier": "POI-5056",
            "title": "Research a flaky close error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_handles_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "To Research",
                    "id": "POI-5056",
                    "title": "Research a flaky close error",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5056",
                "title": "Research a flaky close error",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_handles_change_object_new_value(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"oldValue": "Todo", "newValue": "To Research"}},
            "issue": {
                "identifier": "POI-5056",
                "title": "Research a flaky close error",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5056",
                "title": "Research a flaky close error",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title_and_issue_id(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Needs id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-5056"})
        )

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-5056 ",
            "title": "  Research a flaky close error  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5056",
            "title": "Research a flaky close error",
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
                "issueId": "POI-5056",
                "title": "Cursor researching: Research a flaky close error",
            },
        )


if __name__ == "__main__":
    unittest.main()
