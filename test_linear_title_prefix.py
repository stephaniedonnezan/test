import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3626",
                "title": "[FE] Refine the Meters Page dialogs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: [FE] Refine the Meters Page dialogs",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1234",
            "title": "Investigate meter export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate meter export",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-3626",
                "title": "Refine the Meters Page dialogs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_payloads(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-1234",
            "title": "Investigate meter export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-1234",
            "title": "cursor researching: Investigate meter export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_changes_payload_uses_identifier(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {
                "state": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5678",
                "title": "Review meter dialog states",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5678",
                "title": "Cursor researching: Review meter dialog states",
            },
        )

    def test_linear_updated_from_state_id_falls_back_to_current_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-2468",
                "title": "Research meter readings",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2468",
                "title": "Cursor researching: Research meter readings",
            },
        )

    def test_generic_issue_update_without_status_change_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5678",
                "title": "Review meter dialog states",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title_and_issue_id(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-9999",
            "title": "User removal flow",
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
                "issueId": "POI-9999",
                "title": "Cursor researching: User removal flow",
            },
        )


if __name__ == "__main__":
    unittest.main()
