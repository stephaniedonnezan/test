import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4943",
                "title": "User Feedback: Typo in certification name",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4943",
                "title": "Cursor researching: User Feedback: Typo in certification name",
            },
        )

    def test_ignores_other_destination_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4943",
                "title": "User Feedback: Typo in certification name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4943",
                "title": "User Feedback: Typo in certification name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4943",
                "title": "cursor researching: User Feedback: Typo in certification name",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4943",
                    "title": "User Feedback: Typo in certification name",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4943",
                "title": "Cursor researching: User Feedback: Typo in certification name",
            },
        )

    def test_nested_linear_change_list_uses_change_target(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Investigate RFNBO display copy",
                    "state": {"name": "Todo"},
                }
            },
            "changes": [
                {"field": "status", "from": "Todo", "to": {"name": "To Research"}},
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate RFNBO display copy",
            },
        )

    def test_status_normalization_accepts_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4943",
            "title": "User Feedback: Typo in certification name",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User Feedback: Typo in certification name",
        )

    def test_missing_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "issueId": "POI-4943"}
            )
        )

    def test_cli_prints_title_update(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4943",
                "title": "User Feedback: Typo in certification name",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4943",
                "title": "Cursor researching: User Feedback: Typo in certification name",
            },
        )


if __name__ == "__main__":
    unittest.main()
