import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4575",
            "title": "Mass balance export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4575",
                "title": "Cursor researching: Mass balance export",
            },
        )

    def test_reads_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "Investigate title prefix",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate title prefix",
            },
        )

    def test_accepts_normalized_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-456",
            "title": "Handle camel case",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Handle camel case",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to-research",
            "identifier": "POI-789",
            "title": "Fallback status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Fallback status",
            },
        )

    def test_reads_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-101",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_prefers_nested_issue_id_over_outer_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-202",
                    "title": "Nested issue id",
                    "status": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-202",
                "title": "Cursor researching: Nested issue id",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-111",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-222",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-333",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-444",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-555",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-555",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
