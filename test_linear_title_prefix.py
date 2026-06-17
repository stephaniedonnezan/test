import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5000",
                "title": "Export and Import are global",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-5000",
                "title": "Cursor researching: Export and Import are global",
            },
        )

    def test_prefixes_nested_cursor_trigger_context_payload(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": " POI-5000 ",
                    "title": "  Export scope is confusing  ",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-5000",
                "title": "Cursor researching: Export scope is confusing",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5000",
                "title": "Export and Import are global",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5000",
                "title": "Export and Import are global",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5000",
                "title": "cursor researching: Export and Import are global",
            }
        )

        self.assertIsNone(result)

    def test_handles_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "id": "linear-uuid",
                    "identifier": "POI-5000",
                    "title": "Export and Import are global",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-5000",
                "title": "Cursor researching: Export and Import are global",
            },
        )

    def test_generic_update_must_include_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["title"],
                "data": {
                    "identifier": "POI-5000",
                    "title": "Export and Import are global",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "ToResearch",
                "id": "POI-5000",
                "title": "Export and Import are global",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5000",
                "title": "Cursor researching: Export and Import are global",
            },
        )


if __name__ == "__main__":
    unittest.main()
