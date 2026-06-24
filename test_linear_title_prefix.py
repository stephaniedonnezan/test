import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_cursor_trigger_context(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4926",
            "title": "Methanation: H2 consumed batch is forwarded to the next month",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4926",
                "title": "Cursor researching: Methanation: H2 consumed batch is forwarded to the next month",
            },
        )

    def test_accepts_cloud_automation_trigger_info(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4926",
                    "title": "Methanation title",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4926",
                "title": "Cursor researching: Methanation title",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4926",
                    "title": "Nested title",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4926",
                "title": "Cursor researching: Nested title",
            },
        )

    def test_accepts_status_from_changes_mapping(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "issue": {"id": "abc123", "title": "Changed through workflow"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "abc123",
                "title": "Cursor researching: Changed through workflow",
            },
        )

    def test_accepts_status_from_changes_list(self):
        event = {
            "type": "issueUpdated",
            "changes": [{"field": "status", "newValue": "TO_RESEARCH"}],
            "issueId": "POI-4926",
            "title": "List change title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4926",
                "title": "Cursor researching: List change title",
            },
        )

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "key": "POI-4926",
            "title": "Variant title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4926",
                "title": "Cursor researching: Variant title",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4926",
            "title": "Comment title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-4926",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4926",
            "title": "QA title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4926",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4926",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4926",
            "title": "CLI title",
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
                "issueId": "POI-4926",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
