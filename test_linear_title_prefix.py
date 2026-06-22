import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_status_change(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
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

    def test_prefixes_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5033",
                    "title": "  CO2 inputs optional proof file  ",
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

    def test_accepts_camel_case_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-1",
            "title": "Investigate methane inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate methane inputs",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update(self):
        event = {
            "webhookType": "issue",
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

    def test_prefixes_nested_linear_issue_state_update(self):
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

    def test_prefixes_linear_changes_status_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {"id": "issue-id", "title": "Review supplier contract"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Review supplier contract",
            },
        )

    def test_prefixes_workflow_state_changes_update(self):
        event = {
            "action": "updated",
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Todo"},
                    "newValue": {"name": "To Research"},
                }
            },
            "issue": {
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

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5033",
                }
            )
        )

    def test_cli_outputs_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5033",
                "title": "CO2 inputs optional proof file",
            }
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

    def test_cli_prints_nothing_for_unrelated_payload(self):
        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "triggerContext": {
                        "webhookType": "issue",
                        "trigger": "status_changed",
                        "newStatus": "QA",
                        "id": "POI-5033",
                        "title": "CO2 inputs optional proof file",
                    }
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
