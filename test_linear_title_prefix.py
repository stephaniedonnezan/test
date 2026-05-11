import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3309",
                "title": "confirm modifications on POS",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3309",
                "title": "Cursor researching: confirm modifications on POS",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3309",
                "title": "confirm modifications on POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3309",
                "title": "confirm modifications on POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3309",
                "title": "cursor researching: confirm modifications on POS",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-3309",
                "title": "confirm modifications on POS",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: confirm modifications on POS",
        )

    def test_reads_issue_details_from_nested_data(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3309",
                    "title": "confirm modifications on POS",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3309",
                "title": "Cursor researching: confirm modifications on POS",
            },
        )

    def test_handles_linear_webhook_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "issue-uuid",
                "title": "confirm modifications on POS",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: confirm modifications on POS",
            },
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-3309",
            "title": "confirm modifications on POS",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3309",
            "title": "confirm modifications on POS",
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
                "issueId": "POI-3309",
                "title": "Cursor researching: confirm modifications on POS",
            },
        )


if __name__ == "__main__":
    unittest.main()
