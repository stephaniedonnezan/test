import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_for_to_research(self):
        event = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
            "title": "User & permission management (Org Admin)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )

    def test_prefixes_wrapped_cursor_trigger_context(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4960",
                "title": "User & permission management (Org Admin)",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )

    def test_ignores_status_changed_event_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4960",
            "title": "User & permission management (Org Admin)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_event(self):
        event = {
            "trigger": "title_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
            "title": "User & permission management (Org Admin)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
            "title": "Cursor researching: User & permission management (Org Admin)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
            "title": "cursor researching - User & permission management (Org Admin)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4960",
            "title": "User & permission management (Org Admin)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )

    def test_prefixes_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4960",
                    "title": "User & permission management (Org Admin)",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )

    def test_ignores_generic_issue_update_when_state_did_not_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4960",
                    "title": "User & permission management (Org Admin)",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changed_field_dict_payload(self):
        event = {
            "action": "update",
            "changes": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4960",
                    "title": "User & permission management (Org Admin)",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "User & permission management (Org Admin)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4960",
            "title": "User & permission management (Org Admin)",
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
                "issueId": "POI-4960",
                "title": "Cursor researching: User & permission management (Org Admin)",
            },
        )


if __name__ == "__main__":
    unittest.main()
