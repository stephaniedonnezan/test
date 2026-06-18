import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4963",
                "title": "cursor researching: User role & rights cannot be seen by invitee",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_generic_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-4963",
                    "title": "User role & rights cannot be seen by invitee",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4963",
                    "title": "User role & rights cannot be seen by invitee",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "webhookType": "Issue Updated",
            "changes": {"status": {"newValue": "ToResearch"}},
            "issueId": "POI-4963",
            "title": "User role & rights cannot be seen by invitee",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
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
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )


if __name__ == "__main__":
    unittest.main()
