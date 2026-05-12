import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "Remove old table columns",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove old table columns",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4637",
                "title": "Remove old table columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "Remove old table columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4637",
                "title": "cursor researching: Remove old table columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_trigger_casing(self):
        event = {
            "triggerContext": {
                "trigger": "StatusChanged",
                "new_status": "to-research",
                "issueId": "POI-4637",
                "title": "Remove old table columns",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Remove old table columns",
        )

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-123",
                "identifier": "POI-4637",
                "title": "Remove old table columns",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove old table columns",
            },
        )

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4637",
                "title": "Remove old table columns",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_updated_from_state_id_as_status_change_signal(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-4637",
                "title": "Remove old table columns",
                "workflowState": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4637",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Remove old table columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_reads_json_from_stdin(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "Remove old table columns",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove old table columns",
            },
        )


if __name__ == "__main__":
    unittest.main()
