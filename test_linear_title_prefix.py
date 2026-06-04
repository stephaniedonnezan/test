import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_cursor_status_change_payload(self):
        payload = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4442",
                "title": "Single POS issuance outside container logic - production site",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4442",
                "title": (
                    "Cursor researching: "
                    "Single POS issuance outside container logic - production site"
                ),
            },
        )

    def test_accepts_status_case_and_separator_variants(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "TO_RESEARCH",
                "issueId": "POI-1",
                "title": "Research me",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Research me",
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-2",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_accepts_changes_payload_with_to_status(self):
        payload = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Todo"},
                    "to": {"name": "to research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Changed via workflow state",
                    "workflowState": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Changed via workflow state",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4442",
                "title": "Single POS issuance outside container logic - production site",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_change_events(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "to research",
                "id": "POI-4442",
                "title": "Single POS issuance outside container logic - production site",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_issue_updates_without_status_field_changes(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Title-only update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_does_not_duplicate_existing_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "cursor researching: Already prefixed",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_when_issue_identity_is_missing(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_cli_prints_json_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "CLI issue",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
