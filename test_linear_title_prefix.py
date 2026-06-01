import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_automation_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3129",
                "title": "Handle mixtures of compliant and non-compliant CO2 Input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3129",
                "title": "Cursor researching: Handle mixtures of compliant and non-compliant CO2 Input",
            },
        )

    def test_ignores_other_new_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3129",
            "title": "Handle mixtures of compliant and non-compliant CO2 Input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3129",
            "title": "Handle mixtures of compliant and non-compliant CO2 Input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3129",
                    "title": "Handle mixtures of compliant and non-compliant CO2 Input",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3129",
                "title": "Cursor researching: Handle mixtures of compliant and non-compliant CO2 Input",
            },
        )

    def test_accepts_status_changed_camel_case_and_falls_back_to_status(self):
        event = {
            "webhookType": "statusChanged",
            "status": "toResearch",
            "issueId": "POI-3129",
            "title": "  Handle mixtures of compliant and non-compliant CO2 Input  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3129",
                "title": "Cursor researching: Handle mixtures of compliant and non-compliant CO2 Input",
            },
        )

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3129",
            "title": "cursor researching: Handle mixtures of compliant and non-compliant CO2 Input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-3129",
            "title": "Handle mixtures of compliant and non-compliant CO2 Input",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3129",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3129",
            "title": "Handle mixtures of compliant and non-compliant CO2 Input",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3129",
                "title": "Cursor researching: Handle mixtures of compliant and non-compliant CO2 Input",
            },
        )


if __name__ == "__main__":
    unittest.main()
