import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5054",
                "title": "Select All button for POS issuance",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5054",
                "title": "Cursor researching: Select All button for POS issuance",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5054",
                "title": "Select All button for POS issuance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5054",
                "title": "Select All button for POS issuance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-5054",
            "title": "cursor researching: Select All button for POS issuance",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Select All button for POS issuance",
        )

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-5054",
            "title": "Select All button for POS issuance",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Select All button for POS issuance",
        )

    def test_handles_nested_linear_updated_fields_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5054",
                    "title": "Select All button for POS issuance",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5054",
                "title": "Cursor researching: Select All button for POS issuance",
            },
        )

    def test_handles_nested_linear_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Select All button for POS issuance",
                },
                "changes": {"status": {"from": "Todo", "to": "To Research"}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Select All button for POS issuance",
            },
        )

    def test_ignores_generic_updates_without_status_metadata(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-5054",
                    "title": "Select All button for POS issuance",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5054",
                "title": "Select All button for POS issuance",
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
                "issueId": "POI-5054",
                "title": "Cursor researching: Select All button for POS issuance",
            },
        )


if __name__ == "__main__":
    unittest.main()
