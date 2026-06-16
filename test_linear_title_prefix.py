import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4354",
            "title": "Why we only use the first element in this code",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4354",
                "title": (
                    "Cursor researching: "
                    "Why we only use the first element in this code"
                ),
            },
        )

    def test_prefixes_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4354",
                "title": "Why we only use the first element in this code",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4354",
                "title": (
                    "Cursor researching: "
                    "Why we only use the first element in this code"
                ),
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4354",
                "title": "Investigate first unified allocation element",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4354",
                "title": (
                    "Cursor researching: "
                    "Investigate first unified allocation element"
                ),
            },
        )

    def test_accepts_changed_status_new_value(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "issue": {
                "issueId": "POI-4354",
                "title": "Research hydrogen mass balance export allocation",
            },
            "changes": {"status": {"oldValue": "Todo", "newValue": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4354",
                "title": (
                    "Cursor researching: "
                    "Research hydrogen mass balance export allocation"
                ),
            },
        )

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "identifier": "POI-4354",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_prefers_issue_identifier_over_webhook_event_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4354",
                "title": "Use the issue identifier",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4354")

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4354",
            "title": "cursor researching: Existing research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing research issue",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4354",
            "title": "Do not update todo issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4354",
                "title": "Title-only edit",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4354",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_state_name_is_not_used_as_missing_title(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4354",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4354",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4354",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
