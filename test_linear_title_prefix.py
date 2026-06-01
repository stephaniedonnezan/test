import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "Custom LHV",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4733",
                "title": "Custom LHV",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "Custom LHV",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4733",
                "title": "cursor researching: Custom LHV",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4733",
                "title": "Custom LHV",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Custom LHV",
        )

    def test_accepts_nested_linear_update_payload_with_changed_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4733",
                "title": "Custom LHV",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_requires_status_field_for_generic_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4733",
                "title": "Custom LHV",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_nested_issue_identifier_over_outer_automation_id(self):
        event = {
            "id": "automation-id",
            "action": "update",
            "updatedFields": {"workflowState": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "identifier": "POI-4733",
                    "title": "Custom LHV",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4733")

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": " POI-4733 ",
                "title": " Custom LHV ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_returns_none_for_missing_issue_details(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_as_json(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "Custom LHV",
            },
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )


if __name__ == "__main__":
    unittest.main()
