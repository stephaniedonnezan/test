import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4832",
            "title": "GoO Cancelation upload supports multiple documents",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: GoO Cancelation upload supports multiple documents",
            },
        )

    def test_supports_cursor_trigger_context_payloads(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4832",
                "title": "Energy allocation documents",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )

    def test_ignores_status_changed_events_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4832",
                "title": "Energy allocation documents",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4832",
            "title": "Energy allocation documents",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4832",
            "title": "cursor researching: Energy allocation documents",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_name_case_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "identifier": "POI-4832",
            "title": "Energy allocation documents",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )

    def test_supports_nested_linear_issue_update_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4832",
                    "title": "Energy allocation documents",
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )

    def test_ignores_generic_update_without_status_changed_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "identifier": "POI-4832",
            "title": "Energy allocation documents",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_current_state_name_when_status_change_has_no_new_status_key(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "key": "POI-4832",
            "title": "Energy allocation documents",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4832 ",
            "title": " Energy allocation documents ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4832"}
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4832",
            "title": "Energy allocation documents",
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
                "issueId": "POI-4832",
                "title": "Cursor researching: Energy allocation documents",
            },
        )


if __name__ == "__main__":
    unittest.main()
