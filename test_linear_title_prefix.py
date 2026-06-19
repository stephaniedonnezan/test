import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-5078",
                "title": "Error: Deliveries not fully allocated",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5078",
                "title": "Cursor researching: Error: Deliveries not fully allocated",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5078",
                "title": "Error: Deliveries not fully allocated",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5078",
                "title": "Error: Deliveries not fully allocated",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-5078",
                "title": "cursor researching: Error: Deliveries not fully allocated",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-5078",
                "title": "Allocation follow-up",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5078",
                "title": "Cursor researching: Allocation follow-up",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-5078",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5078",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_prefers_explicit_new_status_over_current_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "status": "In Progress",
                "id": "POI-5078",
                "title": "Status transition race",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Status transition race",
        )

    def test_reads_new_status_from_change_map(self):
        event = {
            "action": "update",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "identifier": "POI-5078",
                "title": "Change map title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5078",
                "title": "Cursor researching: Change map title",
            },
        )

    def test_requires_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5078",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_payload_without_trigger_when_status_change_is_explicit(self):
        event = {
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5078",
                    "title": "Workflow state title",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow state title",
        )

    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to-research",
                "id": "POI-5078",
                "title": "CLI title",
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
                "issueId": "POI-5078",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
