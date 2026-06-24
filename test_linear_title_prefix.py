import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_returns_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4419",
                "title": "Cursor researching: [] error during MB download (Hy2gen)",
            },
        )

    def test_cursor_automation_trigger_context_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4419",
                    "title": "[] error during MB download (Hy2gen)",
                }
            }
        }

        action = build_issue_title_update(event)

        self.assertIsNotNone(action)
        self.assertEqual(action["issueId"], "POI-4419")

    def test_direct_trigger_context_is_supported(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4419",
                "title": "[] error during MB download (Hy2gen)",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: [] error during MB download (Hy2gen)",
        )

    def test_status_matching_accepts_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4419",
            "title": "Mass balance download error",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Mass balance download error",
        )

    def test_nested_linear_issue_update_with_updated_state_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4419",
                    "title": "[] error during MB download (Hy2gen)",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: [] error during MB download (Hy2gen)",
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4419",
            "title": "cursor researching: [] error during MB download (Hy2gen)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4419",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_mapping_can_provide_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: [] error during MB download (Hy2gen)",
        )

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4419",
            "title": "[] error during MB download (Hy2gen)",
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
                "issueId": "POI-4419",
                "title": "Cursor researching: [] error during MB download (Hy2gen)",
            },
        )


if __name__ == "__main__":
    unittest.main()
