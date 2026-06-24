import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4368",
                "title": "Change the pre-push git hook in husky",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4368",
                "title": "Cursor researching: Change the pre-push git hook in husky",
            },
        )

    def test_prefixes_nested_cursor_trigger_context_payload(self):
        action = build_issue_title_update(
            {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Change the pre-push git hook in husky",
                    "id": "POI-4368",
                    "url": "https://linear.app/atmen/issue/POI-4368/example",
                    "status": "To Research",
                    "statusType": "started",
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4368",
                "title": "Cursor researching: Change the pre-push git hook in husky",
            },
        )

    def test_prefixes_linear_update_when_status_field_changed(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "id": "event-id",
                    "issue": {
                        "identifier": "POI-4368",
                        "title": "Research issue title update",
                        "state": {"name": "To Research"},
                    },
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4368",
                "title": "Cursor researching: Research issue title update",
            },
        )

    def test_uses_explicit_changed_status_before_stale_issue_state(self):
        action = build_issue_title_update(
            {
                "action": "Issue Updated",
                "changes": {"status": {"from": "Backlog", "to": "to research"}},
                "issue": {
                    "id": "POI-4368",
                    "title": "Changed status payload",
                    "status": {"name": "Backlog"},
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4368",
                "title": "Cursor researching: Changed status payload",
            },
        )

    def test_ignores_non_status_update(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["title"],
                    "newStatus": "to research",
                    "id": "POI-4368",
                    "title": "Only title changed",
                }
            )
        )

    def test_ignores_other_status(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "DEV",
                    "id": "POI-4368",
                    "title": "Do not prefix",
                }
            )
        )

    def test_ignores_already_prefixed_title_case_insensitively(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4368",
                    "title": "cursor researching: Existing prefix",
                }
            )
        )

    def test_cli_prints_action_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-4368",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4368",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
