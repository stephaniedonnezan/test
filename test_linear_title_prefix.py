import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_change_context(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4639",
            "title": "Methane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_builds_update_for_automation_trigger_context(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4639",
                "title": "Methane",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_ignores_other_new_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4639",
                "title": "Methane",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4639",
            "title": "Methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4639",
            "title": "Cursor researching: Methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4639",
            "title": "cursor researching - Methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_normalized_status_spellings(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4639",
            "title": "Methane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_reads_nested_linear_issue_update_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "identifier": "POI-4639",
                    "title": "Methane",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_ignores_generic_issue_updates_without_status_field(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4639",
                    "title": "Methane",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_change_to_value(self):
        event = {
            "action": "update",
            "changes": {
                "state": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                },
            },
            "issueId": "POI-4639",
            "title": "Methane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Methane",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4639",
                }
            )
        )

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4639",
            "title": "Methane",
        }

        result = subprocess.run(
            [sys.executable, "-m", "linear_title_prefix"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4639",
                "title": "Cursor researching: Methane",
            },
        )


if __name__ == "__main__":
    unittest.main()
