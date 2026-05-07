import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_moved_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "cursor researching: Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_reads_status_from_state_name(self):
        event = {
            "triggerContext": {
                "trigger": "state_changed",
                "state": {"name": "To Research"},
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_accepts_linear_data_issue_envelope(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "state": {"name": "to research"},
                "issue": {
                    "identifier": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_cli_prints_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )


if __name__ == "__main__":
    unittest.main()
