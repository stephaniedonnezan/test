import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5047",
                "title": "What is a valid default downstream emissions name?",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: What is a valid default downstream emissions name?",
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5047",
                    "title": "What is a valid default downstream emissions name?",
                }
            }
        )

        self.assertEqual(
            action["title"],
            "Cursor researching: What is a valid default downstream emissions name?",
        )

    def test_accepts_status_name_variants(self):
        action = build_issue_title_update(
            {
                "webhookType": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-5047",
                "title": "What is a valid default downstream emissions name?",
            }
        )

        self.assertEqual(action["issueId"], "POI-5047")

    def test_skips_status_changes_to_other_statuses(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5047",
                "title": "What is a valid default downstream emissions name?",
            }
        )

        self.assertIsNone(action)

    def test_skips_non_status_change_trigger(self):
        action = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5047",
                "title": "What is a valid default downstream emissions name?",
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_existing_prefix(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5047",
                "title": "cursor researching: What is a valid default downstream emissions name?",
            }
        )

        self.assertEqual(
            action["title"],
            "cursor researching: What is a valid default downstream emissions name?",
        )

    def test_requires_issue_id_and_title(self):
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
                    "title": "What is a valid default downstream emissions name?",
                }
            )
        )

    def test_accepts_generic_linear_issue_update_when_status_field_changed(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["stateId"],
                "data": {
                    "identifier": "POI-5047",
                    "title": "What is a valid default downstream emissions name?",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            action["title"],
            "Cursor researching: What is a valid default downstream emissions name?",
        )

    def test_uses_changed_status_value_from_nested_linear_payload(self):
        action = build_issue_title_update(
            {
                "action": "Issue Updated",
                "changes": {
                    "state": {
                        "from": {"name": "Todo"},
                        "to": {"name": "To Research"},
                    }
                },
                "data": {
                    "issue": {
                        "identifier": "POI-5047",
                        "title": "What is a valid default downstream emissions name?",
                    }
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-5047")
        self.assertEqual(
            action["title"],
            "Cursor researching: What is a valid default downstream emissions name?",
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "What is a valid default downstream emissions name?",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: What is a valid default downstream emissions name?",
            },
        )


if __name__ == "__main__":
    unittest.main()
