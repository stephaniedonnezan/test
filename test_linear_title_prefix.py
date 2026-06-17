import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4954",
                "title": "AI sub-processor disclosure",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4954",
                "title": "Cursor researching: AI sub-processor disclosure",
            },
        )

    def test_uses_current_status_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "issueId": "POI-1000",
            "title": "Review supplier data",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1000",
                "title": "Cursor researching: Review supplier data",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "webhookType": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2222",
                    "title": "Investigate upload path",
                    "state": {"name": "Todo"},
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Todo"},
                    "to": {"name": "ToResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2222",
                "title": "Cursor researching: Investigate upload path",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4954",
                "title": "AI sub-processor disclosure",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4954",
                "title": "AI sub-processor disclosure",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_issue_updates_without_status_change(self):
        event = {
            "webhookType": "Issue",
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-2222",
                    "title": "Investigate upload path",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4954",
            "title": "cursor researching: AI sub-processor disclosure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing an identifier",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4954",
                "title": "AI sub-processor disclosure",
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
                "issueId": "POI-4954",
                "title": "Cursor researching: AI sub-processor disclosure",
            },
        )


if __name__ == "__main__":
    unittest.main()
