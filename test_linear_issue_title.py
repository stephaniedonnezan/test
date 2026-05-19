import json
import subprocess
import sys
import unittest

from linear_issue_title import build_issue_title_update, handle_issue_status_changed


class LinearIssueTitleTest(unittest.TestCase):
    def test_builds_update_for_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-3045",
                "title": '"register storage loss" seems obligatory',
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3045",
                "title": 'Cursor researching: "register storage loss" seems obligatory',
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-3045",
                "title": '"register storage loss" seems obligatory',
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3045",
                "title": '"register storage loss" seems obligatory',
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3045",
                "title": "cursor researching: already marked",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "issue_id": "POI-3045",
                "title": "Needs research",
            }
        }

        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3045",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["stateId"],
            "data": {
                "id": "POI-3045",
                "title": "Needs research",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3045",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_cli_prints_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3045",
                "title": "Needs research",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_issue_title.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3045",
                "title": "Cursor researching: Needs research",
            },
        )


if __name__ == "__main__":
    unittest.main()
