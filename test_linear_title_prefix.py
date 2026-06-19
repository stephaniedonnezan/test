import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing, show discrepancies in batches",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing, show discrepancies in batches",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "TO_RESEARCH",
                "id": "POI-4421",
                "title": "Spreadsheet testing",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4421")
        self.assertEqual(update["title"], "Cursor researching: Spreadsheet testing")

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4421",
                    "title": "Spreadsheet testing",
                    "state": {"name": "ToResearch"},
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4421")
        self.assertEqual(update["title"], "Cursor researching: Spreadsheet testing")

    def test_skips_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "cursor researching: Spreadsheet testing",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Spreadsheet testing",
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4421",
            "title": "Spreadsheet testing",
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
                "issueId": "POI-4421",
                "title": "Cursor researching: Spreadsheet testing",
            },
        )


if __name__ == "__main__":
    unittest.main()
