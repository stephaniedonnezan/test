import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3610",
            "title": "Create a function to auto assign end-trip activity",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3610",
                "title": "Cursor researching: Create a function to auto assign end-trip activity",
            },
        )

    def test_supports_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-1234",
                    "title": "Investigate transport event handling",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate transport event handling",
            },
        )

    def test_ignores_other_target_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3610",
            "title": "Create a function",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3610",
            "title": "Create a function",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_RESEARCH",
            "issueId": "POI-4321",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3610",
            "title": "cursor researching: Create a function",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5678",
                    "title": "Research Linear webhook shape",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5678",
                "title": "Cursor researching: Research Linear webhook shape",
            },
        )

    def test_ignores_generic_issue_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5678",
                    "title": "Research Linear webhook shape",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_changes_map_and_workflow_state_name(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"oldValue": "Backlog"}},
            "issue": {
                "identifier": "POI-2468",
                "title": "Handle workflow state payloads",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Handle workflow state payloads",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "No id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9999",
            "title": "Run from stdin",
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
                "issueId": "POI-9999",
                "title": "Cursor researching: Run from stdin",
            },
        )


if __name__ == "__main__":
    unittest.main()
