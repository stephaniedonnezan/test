import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_prefixes_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5018",
                "title": "High GO amount saves",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: High GO amount saves",
            },
        )

    def test_accepts_normalized_status_and_trigger_names(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "identifier": "POI-5018",
            "title": "Normalize variants",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Normalize variants",
            },
        )

    def test_prefixes_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "linear-internal-id",
                    "identifier": "POI-5018",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-internal-id",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5018",
            "title": "cursor researching: Existing prefix",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "cursor researching: Existing prefix",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5018",
            "title": "No prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5018",
            "title": "No prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-5018",
            "title": "No prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5018",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
