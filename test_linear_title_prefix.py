import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_trigger_context(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5053",
                "title": "Cursor researching: Grey batches allocation issues",
            },
        )

    def test_builds_update_for_automation_trigger_info_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5053",
                    "title": "Grey batches allocation issues",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5053",
                "title": "Cursor researching: Grey batches allocation issues",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Grey batches allocation issues")

    def test_accepts_status_with_separators(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to_research",
            "identifier": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-5053")

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5053",
            "title": "cursor researching: Grey batches allocation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5053",
                "title": "Grey batches allocation issues",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5053",
                "title": "Cursor researching: Grey batches allocation issues",
            },
        )

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5053",
                "title": "Grey batches allocation issues",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changes_map_new_value(self):
        event = {
            "action": "updated",
            "type": "Issue",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "data": {
                "identifier": "POI-5053",
                "title": "Grey batches allocation issues",
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-5053")

    def test_accepts_changes_list_field_new_value(self):
        event = {
            "action": "updated",
            "type": "Issue",
            "changes": [
                {"field": "workflowState", "oldValue": "Backlog", "newValue": "To Research"}
            ],
            "data": {
                "identifier": "POI-5053",
                "title": "Grey batches allocation issues",
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Grey batches allocation issues")

    def test_ignores_invalid_payload(self):
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5053",
            "title": "Grey batches allocation issues",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5053",
                "title": "Cursor researching: Grey batches allocation issues",
            },
        )


if __name__ == "__main__":
    unittest.main()
