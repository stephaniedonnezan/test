import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4736",
                "title": "[Backend] Scaffold delivery-transport-emissions lib + ports",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4736",
                "title": "Cursor researching: [Backend] Scaffold delivery-transport-emissions lib + ports",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "To Research",
            "issueId": "POI-1",
            "title": "Research this issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_accepts_separator_and_case_variants_for_status(self):
        event = {
            "trigger": "status-change",
            "new_status": "To_Research",
            "id": "POI-2",
            "title": "Normalize status variants",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status variants",
        )

    def test_returns_none_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-3",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Existing work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-webhook-id",
                    "identifier": "POI-6",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-webhook-id",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "POI-7",
                    "title": "Not a status update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_workflow_state_name(self):
        event = {
            "webhookType": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-8",
                    "title": "Workflow state payload",
                    "workflowState": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow state payload",
        )

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "CLI issue",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
