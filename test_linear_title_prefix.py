import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3091",
                "title": "[FE] Dialog refinment",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3091",
                "title": "Cursor researching: [FE] Dialog refinment",
            },
        )

    def test_flat_status_changed_event(self):
        event = {
            "webhookType": "issue",
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-1",
            "title": "Investigate rate limit",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate rate limit",
        )

    def test_nested_linear_issue_update_with_updated_from_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "linear-uuid",
                "title": "Audit dialog inventory",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "previous-state-uuid"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Audit dialog inventory",
            },
        )

    def test_changes_payload_accepts_camel_case_status(self):
        event = {
            "issue": {
                "identifier": "POI-2",
                "title": "Research API behavior",
            },
            "changes": {
                "workflowState": {
                    "from": "Backlog",
                    "to": "toResearch",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research API behavior",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-3",
            "title": "Build feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_research_status_without_change_signal(self):
        event = {
            "id": "POI-4",
            "title": "Already researching",
            "status": "to research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_details(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_ignores_already_prefixed_title(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_json(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "CLI example",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: CLI example",
            },
        )


if __name__ == "__main__":
    unittest.main()
