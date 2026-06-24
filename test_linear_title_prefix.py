import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_cursor_trigger_moves_issue_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4502",
                "title": "[Trader MB] External inputs showing in Feb. MB",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4502",
                "title": "Cursor researching: [Trader MB] External inputs showing in Feb. MB",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4502",
                "title": "Needs verification",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4502",
                "title": "Investigate title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4502",
                "title": "cursor researching: Investigate title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "To_Research",
                "issue_id": "POI-4502",
                "title": "Investigate title",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4502",
                "title": "Cursor researching: Investigate title",
            },
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4502",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4502",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "POI-4502",
                    "title": "Title-only change",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_status_field_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4502",
                "title": "Fallback status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4502",
                "title": "Cursor researching: Fallback status",
            },
        )

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-4502"})
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4502",
                "title": "CLI title",
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
                "issueId": "POI-4502",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
