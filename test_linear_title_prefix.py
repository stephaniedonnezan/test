import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": '[]Supply contract only states "producer"',
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": 'Cursor researching: []Supply contract only states "producer"',
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-5045",
                "title": "Supply contract wording",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "label_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "Supply contract wording",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "cursor researching: Supply contract wording",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-5045",
                "title": "Supply contract wording",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract wording",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract wording",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract wording",
            },
        )

    def test_uses_change_destination_before_current_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": {"name": "Backlog"}, "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract wording",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract wording",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5045",
                    "title": "Supply contract wording",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_or_id_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-5045",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Supply contract wording",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5045",
                "title": "Supply contract wording",
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
                "issueId": "POI-5045",
                "title": "Cursor researching: Supply contract wording",
            },
        )


if __name__ == "__main__":
    unittest.main()
