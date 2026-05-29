import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "Missing UBA POS preview in Container Logic Closing tab.",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview in Container Logic Closing tab.",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4680",
                "title": "Missing UBA POS preview in Container Logic Closing tab.",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4680",
                "title": "Missing UBA POS preview in Container Logic Closing tab.",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4680",
            "title": "cursor researching: Missing UBA POS preview",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status_and_identifier(self):
        event = {
            "trigger": "stateChanged",
            "newStatus": "toResearch",
            "identifier": "POI-4680",
            "title": "Missing UBA POS preview",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "identifier": "POI-4680",
                    "title": "Missing UBA POS preview",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin_123",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )

    def test_ignores_issue_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "POI-4680",
                    "title": "Missing UBA POS preview",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_workflow_state_status_name(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "POI-4680",
                "title": "Missing UBA POS preview",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing UBA POS preview",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4680",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4680",
            "title": "Missing UBA POS preview",
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
                "issueId": "POI-4680",
                "title": "Cursor researching: Missing UBA POS preview",
            },
        )


if __name__ == "__main__":
    unittest.main()
