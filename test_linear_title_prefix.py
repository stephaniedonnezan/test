import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4313",
                "title": "Weird cancel button on the delivery dialog",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4313",
                "title": "Cursor researching: Weird cancel button on the delivery dialog",
            },
        )

    def test_accepts_direct_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To_Research",
            "issueId": "POI-1",
            "title": "Research the dashboard",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research the dashboard",
            },
        )

    def test_accepts_hyphenated_target_status(self):
        event = {
            "trigger": "status-changed",
            "new_status": "to-research",
            "identifier": "POI-2",
            "title": "Review reports",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Review reports",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4313",
            "title": "Weird cancel button on the delivery dialog",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4313",
            "title": "Weird cancel button on the delivery dialog",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "cursor researching: Already queued",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_with_updated_state_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4",
                "title": "Clarify import errors",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Clarify import errors",
            },
        )

    def test_accepts_nested_linear_change_new_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Revisit delivery modal",
                },
                "changes": {
                    "workflowState": {
                        "oldValue": {"name": "Backlog"},
                        "newValue": {"name": "to research"},
                    },
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Revisit delivery modal",
            },
        )

    def test_generic_issue_update_without_status_metadata_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-6",
                "title": "Only the description changed",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "Run a smoke test",
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
                "issueId": "POI-8",
                "title": "Cursor researching: Run a smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
