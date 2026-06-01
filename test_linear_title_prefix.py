import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4728",
                "title": "CO2 mass balance, monthly carry with RFNBO",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4728",
                "title": "Cursor researching: CO2 mass balance, monthly carry with RFNBO",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4728",
                "title": "CO2 mass balance, monthly carry with RFNBO",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4728",
                "title": "CO2 mass balance, monthly carry with RFNBO",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4728",
                "title": "cursor researching: CO2 mass balance",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4728",
                "title": "CO2 mass balance, monthly carry with RFNBO",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: CO2 mass balance, monthly carry with RFNBO",
            },
        )

    def test_skips_nested_update_when_state_did_not_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-uuid",
                "title": "CO2 mass balance, monthly carry with RFNBO",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_trigger_context_nested_data(self):
        event = {
            "triggerContext": {
                "action": "Issue Updated",
                "updatedFields": [{"field": "workflowState"}],
                "data": {
                    "issue": {
                        "id": "nested-issue-id",
                        "title": "A title",
                        "workflowState": {"name": "toResearch"},
                    },
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "nested-issue-id",
                "title": "Cursor researching: A title",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4728",
            "title": "CO2 mass balance",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4728",
                "title": "Cursor researching: CO2 mass balance",
            },
        )


if __name__ == "__main__":
    unittest.main()
