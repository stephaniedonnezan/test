import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_status_changed_trigger_adds_prefix(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4963",
                "title": "User role & rights cannot be seen by invitee",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4963",
                "title": "Cursor researching: User role & rights cannot be seen by invitee",
            },
        )

    def test_accepts_flat_trigger_context_as_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "Investigate permissions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate permissions",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "description_changed",
                "newStatus": "To Research",
                "id": "POI-2",
                "title": "Investigate permissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-3",
                "title": "Investigate permissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "cursor researching: Investigate permissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Investigate permissions",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFrom": {"stateId": "old-state"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Investigate permissions",
            },
        )

    def test_reads_status_from_change_metadata(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-6",
                "title": "Investigate permissions",
            },
            "changes": {"state": {"to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Investigate permissions",
            },
        )

    def test_handles_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "to_research",
                "id": "POI-7",
                "title": "Investigate permissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Investigate permissions",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": " To Research ",
                "id": " POI-8 ",
                "title": " Investigate permissions ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Investigate permissions",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Investigate permissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-9",
                "title": "Investigate permissions",
            }
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
                "issueId": "POI-9",
                "title": "Cursor researching: Investigate permissions",
            },
        )


if __name__ == "__main__":
    unittest.main()
