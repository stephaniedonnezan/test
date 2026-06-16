import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4999",
                "title": "If no loading event, still show production amount in site view",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: If no loading event, still show production amount in site view",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4999",
                "title": "If no loading event, still show production amount in site view",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4999",
                "title": "If no loading event, still show production amount in site view",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4999",
                "title": "cursor researching: If no loading event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-4999",
                    "id": "uuid-value",
                    "title": "If no loading event",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: If no loading event",
            },
        )

    def test_accepts_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4999",
                    "title": "If no loading event",
                }
            },
            "changes": [
                {
                    "field": "workflowState",
                    "from": {"name": "Backlog"},
                    "to": {"name": "toResearch"},
                }
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: If no loading event",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4999",
                "title": "If no loading event",
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
                "issueId": "POI-4999",
                "title": "Cursor researching: If no loading event",
            },
        )


if __name__ == "__main__":
    unittest.main()
