import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4939",
            "title": "2026-06-15-DailyReport",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4939",
                "title": "Cursor researching: 2026-06-15-DailyReport",
            },
        )

    def test_reads_payload_from_automation_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4939",
                "title": "2026-06-15-DailyReport",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4939",
                "title": "Cursor researching: 2026-06-15-DailyReport",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4939",
            "title": "2026-06-15-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4939",
            "title": "2026-06-15-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4939",
            "title": "cursor researching: 2026-06-15-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_spelling(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "identifier": "POI-4939",
            "title": "2026-06-15-DailyReport",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4939",
                "title": "Cursor researching: 2026-06-15-DailyReport",
            },
        )

    def test_accepts_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4939",
                    "title": "2026-06-15-DailyReport",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4939",
                "title": "Cursor researching: 2026-06-15-DailyReport",
            },
        )

    def test_ignores_generic_update_without_status_change_metadata(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4939",
                    "title": "2026-06-15-DailyReport",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_metadata(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"}))

    def test_current_canceled_trigger_payload_is_ignored(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "title": "2026-06-15-DailyReport",
                "id": "POI-4939",
                "status": "Canceled",
                "statusType": "canceled",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4939",
            "title": "2026-06-15-DailyReport",
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
                "issueId": "POI-4939",
                "title": "Cursor researching: 2026-06-15-DailyReport",
            },
        )


if __name__ == "__main__":
    unittest.main()
