import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
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

    def test_uses_trigger_context_from_cursor_automation_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
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

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "state": {"name": "to_research"},
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

    def test_accepts_workflow_state_updated_field(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "workflowState": {"name": "To Research"},
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

    def test_accepts_camel_case_status_and_trigger_values(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CO2 inputs optional proof file",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "cursor researching: CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: CO2 inputs optional proof file",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "status": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )


if __name__ == "__main__":
    unittest.main()
