import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4716",
                "title": "Why the special getContainerDeliveries logic?",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4716",
                "title": "Cursor researching: Why the special getContainerDeliveries logic?",
            },
        )

    def test_normalizes_camel_case_and_hyphenated_status_values(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-1",
            "title": "Investigate import failure",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate import failure",
            },
        )

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "identifier": "POI-2",
                "title": "Nested payload",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_accepts_linear_updated_from_status_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-issue-id",
                "title": "State id changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: State id changed",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4716",
                "title": "Why the special getContainerDeliveries logic?",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-3",
                "title": "Title changed only",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "cursor researching: Already being researched",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-5",
            "title": "Alias payload",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "CLI payload",
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
                "issueId": "POI-6",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
