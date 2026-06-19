import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_cursor_automation_trigger_context_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-5033")
        self.assertEqual(
            update["title"],
            "Cursor researching: CO2 inputs optional proof file",
        )

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_issue_details(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_changes_mapping_can_provide_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            },
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_changes_list_can_provide_new_status(self):
        event = {
            "webhookType": "updated",
            "changes": [{"field": "status", "new": {"name": "To Research"}}],
            "issue": {
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
            },
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "cursor researching: CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_other_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_details_are_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )


if __name__ == "__main__":
    unittest.main()
