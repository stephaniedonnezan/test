import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4694",
                    "title": "Centralise error/warning composition",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4694",
                "title": "Cursor researching: Centralise error/warning composition",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "id": "POI-4694",
                "title": "Centralise error/warning composition",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4694",
            "title": "Centralise error/warning composition",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status_separators(self):
        event = {
            "webhookType": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "Investigate mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate mass balance",
            },
        )

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "cursor researching: Investigate mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_with_state_field_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Investigate mass balance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate mass balance",
            },
        )

    def test_ignores_generic_update_without_status_change_marker(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Investigate mass balance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "identifier": "POI-123",
            "title": "Investigate mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate mass balance",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                }
            )
        )

        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Investigate mass balance",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate mass balance",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate mass balance",
            },
        )


if __name__ == "__main__":
    unittest.main()
