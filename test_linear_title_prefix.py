import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement delivery transport segment",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4703",
                "title": "Implement delivery transport segment",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement delivery transport segment",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4703",
                "title": "cursor researching: Implement delivery transport segment",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "TO_RESEARCH",
                "identifier": "POI-4703",
                "title": "Implement delivery transport segment",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "Todo"}},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Implement delivery transport segment",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_uses_explicit_new_status_before_nested_status_values(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement delivery transport segment",
                "state": {"name": "Backlog"},
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_does_not_use_updated_from_as_new_status(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "To Research"}},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Implement delivery transport segment",
                    "state": {"name": "In Review"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4703",
                    "title": "Implement delivery transport segment",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": " to research ",
                "issueId": " POI-4703 ",
                "title": " Implement delivery transport segment ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_handles_workflow_state_name(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4703",
                    "title": "Implement delivery transport segment",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )

    def test_returns_none_for_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))


class CliTest(unittest.TestCase):
    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "Implement delivery transport segment",
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
                "issueId": "POI-4703",
                "title": "Cursor researching: Implement delivery transport segment",
            },
        )


if __name__ == "__main__":
    unittest.main()
