import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload(self):
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

    def test_supports_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_supports_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO-RESEARCH",
            "issueId": "POI-1",
            "title": "Research fuel inputs",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research fuel inputs",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_with_new_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5033",
            "title": "cursor researching: CO2 inputs optional proof file",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_linear_issue_update_webhook(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5033",
                "title": "CO2 inputs optional proof file",
                "state": {"id": "state-id", "name": "To Research"},
            },
            "updatedFrom": {"stateId": "previous-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_supports_nested_issue_update_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                    "workflowState": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5033",
        )

    def test_supports_changes_payload_new_status(self):
        event = {
            "type": "update",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "identifier": "POI-5033",
            "title": "CO2 inputs optional proof file",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CO2 inputs optional proof file",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-5033 ",
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

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-5033"}
            )
        )

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
            text=True,
            capture_output=True,
            check=True,
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
