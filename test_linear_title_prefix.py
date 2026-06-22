import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_to_research(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5073",
                "title": "Backend e2e to test scenarios is escapable by user",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5073",
                "title": (
                    "Cursor researching: Backend e2e to test scenarios is "
                    "escapable by user"
                ),
            },
        )

    def test_accepts_status_name_from_nested_linear_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-5073",
                    "title": "Investigate mass balance",
                    "status": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5073",
                "title": "Cursor researching: Investigate mass balance",
            },
        )

    def test_accepts_changed_status_target(self):
        event = {
            "action": "update",
            "changes": {"status": {"from": "Backlog", "to": "to_research"}},
            "issue": {"id": "issue-id", "title": "Research emissions rules"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research emissions rules",
            },
        )

    def test_skips_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5073",
            "title": "Investigate mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5073",
            "title": "Investigate mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5073",
            "title": "cursor researching: Investigate mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_json_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5073",
            "title": "Investigate mass balance",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            encoding="utf-8",
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5073",
                "title": "Cursor researching: Investigate mass balance",
            },
        )


if __name__ == "__main__":
    unittest.main()
