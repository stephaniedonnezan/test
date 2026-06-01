import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3814",
            "title": "Calculate transport emission",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3814",
                "title": "Cursor researching: Calculate transport emission",
            },
        )

    def test_reads_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3814",
                "title": "Calculate transport emission",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3814",
                "title": "Cursor researching: Calculate transport emission",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Research carrier emissions",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research carrier emissions",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3814",
            "title": "Calculate transport emission",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3814",
            "title": "Calculate transport emission",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_when_status_was_not_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Research carrier emissions",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-3814",
            "title": "cursor researching: Calculate transport emission",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": " POI-3814 ",
            "title": "  Calculate transport emission  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3814",
                "title": "Cursor researching: Calculate transport emission",
            },
        )

    def test_missing_issue_data_returns_none(self):
        event = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_valid_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3814",
            "title": "Calculate transport emission",
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
                "issueId": "POI-3814",
                "title": "Cursor researching: Calculate transport emission",
            },
        )


if __name__ == "__main__":
    unittest.main()
