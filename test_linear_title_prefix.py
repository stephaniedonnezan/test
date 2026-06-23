import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4822",
                    "title": "Add delivery transport segment entity",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4822",
                "title": "Cursor researching: Add delivery transport segment entity",
            },
        )

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-1",
                "title": "Investigate booking flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate booking flow",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4822",
            "title": "Add delivery transport segment entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4822",
            "title": "Add delivery transport segment entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4822",
            "title": "cursor researching: Add delivery transport segment entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4822",
                    "title": "Add delivery transport segment entity",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {"state": {"from": {"name": "Todo"}, "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4822",
                "title": "Cursor researching: Add delivery transport segment entity",
            },
        )

    def test_requires_updated_status_field_for_generic_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4822",
            "title": "Add delivery transport segment entity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changed_status_before_stale_nested_issue_state(self):
        event = {
            "webhookType": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4822",
                    "title": "Add delivery transport segment entity",
                    "workflowState": {"name": "In Progress"},
                }
            },
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "In Progress"},
                    "newValue": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4822",
                "title": "Cursor researching: Add delivery transport segment entity",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Research"})
        )


class CommandLineTest(unittest.TestCase):
    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4822",
            "title": "Add delivery transport segment entity",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4822",
                "title": "Cursor researching: Add delivery transport segment entity",
            },
        )


if __name__ == "__main__":
    unittest.main()
