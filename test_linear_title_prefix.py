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
            "id": "POI-5047",
            "title": "What is a valid default downstream emissions name?",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": (
                    "Cursor researching: "
                    "What is a valid default downstream emissions name?"
                ),
            },
        )

    def test_prefixes_nested_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "id": "POI-5047",
                "title": "Name validation is unclear",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Name validation is unclear",
            },
        )

    def test_prefixes_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-5047",
                    "title": "Research the downstream emissions name",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Research the downstream emissions name",
            },
        )

    def test_prefixes_generic_issue_update_with_workflow_state_change(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "title": "Needs research title marker",
                    "workflowState": {"name": "To-Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Needs research title marker",
            },
        )

    def test_does_not_update_when_status_is_not_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5047",
            "title": "What is a valid default downstream emissions name?",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_unrelated_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "What is a valid default downstream emissions name?",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5047",
                    "title": "Description-only change",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": " POI-5047 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_returns_none_for_missing_title_or_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5047",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5047",
                "title": "CLI payload",
            }
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
                "issueId": "POI-5047",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
