import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
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

    def test_prefixes_cloud_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-5033")
        self.assertEqual(
            update["title"], "Cursor researching: CO2 inputs optional proof file"
        )

    def test_prefixes_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "id": "uuid-123",
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

    def test_prefixes_change_payload_with_field_and_to_value(self):
        event = {
            "type": "Issue Updated",
            "changes": [{"field": "workflowState", "to": {"name": "toResearch"}}],
            "issue": {
                "identifier": "POI-5033",
                "title": "CO2 inputs optional proof file",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CO2 inputs optional proof file",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_with_research_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5033",
            "title": "cursor researching: CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " POI-5033 ",
            "title": " CO2 inputs optional proof file ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

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
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(json.loads(completed.stdout), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
