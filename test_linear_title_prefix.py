import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4767",
            "title": "2026-05-28-DailyReport",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4767",
                "title": "Cursor researching: 2026-05-28-DailyReport",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to_research",
                "id": "POI-4735",
                "title": "Check CO2 metered reading values",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4735",
                "title": "Cursor researching: Check CO2 metered reading values",
            },
        )

    def test_accepts_linear_update_payload_with_changed_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4761",
                    "title": "Errors still occurring when uploading",
                    "state": {"name": "ToResearch"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4761",
                "title": "Cursor researching: Errors still occurring when uploading",
            },
        )

    def test_uses_explicit_new_status_before_nested_stale_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "data": {
                "id": "POI-4758",
                "title": "Add database checks",
                "state": {"name": "Todo"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4758",
                "title": "Cursor researching: Add database checks",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "Ticket",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4767",
            "title": "2026-05-28-DailyReport",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_when_status_field_was_not_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-1",
                "title": "Ticket",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_marker(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "cursor researching: Ticket",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-1",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Ticket",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-99",
            "title": "Investigate upload failures",
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
                "issueId": "POI-99",
                "title": "Cursor researching: Investigate upload failures",
            },
        )


if __name__ == "__main__":
    unittest.main()
