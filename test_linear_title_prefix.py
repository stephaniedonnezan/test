import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_to_research_updates_title(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5002",
                "title": "PPA supply can be checked as RFNBO in settings",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5002",
                "title": "Cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        )

    def test_non_target_status_is_ignored(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5002",
                "title": "PPA supply can be checked as RFNBO in settings",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5002",
                "title": "PPA supply can be checked as RFNBO in settings",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5002",
                "title": "cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_normalizes_separators_and_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "TO-RESEARCH",
                "id": "POI-5002",
                "title": " PPA supply can be checked as RFNBO in settings ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5002",
                "title": "Cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        )

    def test_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5002",
                    "title": "PPA supply can be checked as RFNBO in settings",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5002",
                "title": "Cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        )

    def test_nested_linear_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5002",
                    "title": "PPA supply can be checked as RFNBO in settings",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_change_payload_new_value_can_supply_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"newValue": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5002",
                    "title": "PPA supply can be checked as RFNBO in settings",
                    "state": {"name": "Backlog"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5002",
                "title": "Cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "PPA supply can be checked as RFNBO in settings",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5002",
                "title": "PPA supply can be checked as RFNBO in settings",
            },
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
                "issueId": "POI-5002",
                "title": "Cursor researching: PPA supply can be checked as RFNBO in settings",
            },
        )


if __name__ == "__main__":
    unittest.main()
