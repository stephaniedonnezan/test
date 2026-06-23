import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload_for_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5109",
                "title": "00 - E2E acceptance suite (TDD - write FIRST)",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5109",
                "title": (
                    "Cursor researching: "
                    "00 - E2E acceptance suite (TDD - write FIRST)"
                ),
            },
        )

    def test_accepts_nested_automation_trigger_info_payload(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5109",
                    "title": "Processor graph acceptance suite",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5109",
                "title": "Cursor researching: Processor graph acceptance suite",
            },
        )

    def test_accepts_normalized_status_name(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-5109",
            "title": "Processor graph acceptance suite",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Processor graph acceptance suite",
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "identifier": "POI-5109",
            "title": "Processor graph acceptance suite",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5109")

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5109",
                "title": "Processor graph acceptance suite",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-5109",
            "title": "Processor graph acceptance suite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-5109",
            "title": "cursor researching: Processor graph acceptance suite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["status"],
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5109",
                    "title": "Processor graph acceptance suite",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5109")

    def test_supports_status_value_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"newValue": {"name": "To Research"}}},
            "issueId": "POI-5109",
            "title": "Processor graph acceptance suite",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Processor graph acceptance suite",
        )

    def test_ignores_generic_update_without_status_change_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "issueId": "POI-5109",
            "title": "Processor graph acceptance suite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_emits_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-5109",
            "title": "Processor graph acceptance suite",
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
                "issueId": "POI-5109",
                "title": "Cursor researching: Processor graph acceptance suite",
            },
        )


if __name__ == "__main__":
    unittest.main()
