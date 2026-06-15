import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_status_changed_to_research_prefixes_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4655",
                "title": "Research how to add plan review",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4655",
                "title": "Cursor researching: Research how to add plan review",
            },
        )

    def test_status_matching_ignores_case_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-123",
                "title": "Check payload handling",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Check payload handling",
            },
        )

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "cursor researching: Check payload handling",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "cursor researching: Check payload handling",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4655",
                "title": "Research how to add plan review",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4655",
                "title": "Research how to add plan review",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_linear_update_payload_uses_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Investigate plan review prompts",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Investigate plan review prompts",
            },
        )

    def test_linear_changes_payload_prefers_new_status_value(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Split research into smaller pieces",
                    "status": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Split research into smaller pieces",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4655",
                "title": "Research how to add plan review",
            }
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
                "issueId": "POI-4655",
                "title": "Cursor researching: Research how to add plan review",
            },
        )


if __name__ == "__main__":
    unittest.main()
