import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_cursor_status_changed_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4167",
                "title": "Add type Mixed in Production Asset Type dropdown",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4167",
                "title": "Cursor researching: Add type Mixed in Production Asset Type dropdown",
            },
        )

    def test_accepts_case_and_separator_variants_for_research_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate balancing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate balancing",
            },
        )

    def test_skips_title_that_already_has_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-2",
            "title": "cursor researching: Investigate balancing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Investigate balancing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4",
            "title": "Investigate balancing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_state_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Research certificate matching",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Research certificate matching",
            },
        )

    def test_accepts_nested_linear_workflow_state_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "identifier": "POI-6",
                "title": "Research contract flow",
                "workflowState": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Research contract flow",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-7",
                "title": "Research contract flow",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changes_new_value_for_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"newValue": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-8",
                "title": "Research contract flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Research contract flow",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Research contract flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "Research contract flow",
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
                "issueId": "POI-10",
                "title": "Cursor researching: Research contract flow",
            },
        )


if __name__ == "__main__":
    unittest.main()
