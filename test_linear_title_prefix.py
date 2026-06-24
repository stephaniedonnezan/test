import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_current_cursor_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5109",
                    "title": "00 - E2E acceptance suite",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5109",
                "title": "Cursor researching: 00 - E2E acceptance suite",
            },
        )

    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-1",
            "title": "Research the importer",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research the importer",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-2",
            "title": "Normalize webhook names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize webhook names",
        )

    def test_accepts_camel_case_automation_trigger_info(self):
        event = {
            "automationTriggerInfo": {
                "triggerContext": {
                    "trigger": "state-changed",
                    "new_state": "to_research",
                    "identifier": "POI-3",
                    "title": "Handle cloud payloads",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-3",
        )

    def test_accepts_generic_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "id": "POI-4",
                    "title": "Investigate regression",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate regression",
        )

    def test_accepts_change_map_new_status_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Map status changes",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "issueId": "POI-6",
            "title": "Do the work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-7",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "issueId": "POI-8",
            "title": "Retitled issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-9",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-10",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-11",
            "title": "Smoke test CLI",
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
                "issueId": "POI-11",
                "title": "Cursor researching: Smoke test CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
