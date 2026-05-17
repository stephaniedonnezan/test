import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "Investigate meter readings",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate meter readings",
            },
        )

    def test_normalizes_status_and_trigger_casing(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-456",
            "title": "Normalize this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Normalize this",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-123",
            "title": "Leave alone",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Leave alone",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_supports_linear_updated_from_state_id(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-101",
                "title": "State id change",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: State id change",
            },
        )

    def test_ignores_update_payload_when_changed_fields_exclude_status(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-123",
                "title": "Description changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-123 ",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-999",
            "title": "CLI issue",
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
                "issueId": "POI-999",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
