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
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4051",
                "title": (
                    "Cursor researching: "
                    "Ensure Manrope is always used in the frontend"
                ),
            },
        )

    def test_cursor_automation_trigger_context_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4051",
                    "title": "Ensure Manrope is always used in the frontend",
                }
            }
        }

        action = build_issue_title_update(event)

        self.assertIsNotNone(action)
        self.assertEqual(action["issueId"], "POI-4051")

    def test_status_matching_accepts_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4051",
            "title": "Frontend font audit",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Frontend font audit",
        )

    def test_nested_linear_issue_update_with_updated_state_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4051",
                    "title": "Ensure Manrope is always used in the frontend",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            (
                "Cursor researching: "
                "Ensure Manrope is always used in the frontend"
            ),
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4051",
            "title": (
                "cursor researching: "
                "Ensure Manrope is always used in the frontend"
            ),
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4051",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_mapping_can_provide_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            (
                "Cursor researching: "
                "Ensure Manrope is always used in the frontend"
            ),
        )

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4051",
            "title": "Ensure Manrope is always used in the frontend",
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
                "issueId": "POI-4051",
                "title": (
                    "Cursor researching: "
                    "Ensure Manrope is always used in the frontend"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
