import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_returns_title_update_for_flat_cursor_status_change_payload(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4966",
                "title": "Invite landing page",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4966",
                "title": "Cursor researching: Invite landing page",
            },
        )

    def test_reads_cursor_trigger_context_payload(self):
        action = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-4966",
                    "title": "Invite landing page",
                },
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Invite landing page")

    def test_accepts_nested_linear_issue_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-4966",
                        "title": "Invite landing page",
                        "state": {"name": "to_research"},
                    }
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4966",
                "title": "Cursor researching: Invite landing page",
            },
        )

    def test_reads_new_status_from_changes_payload(self):
        action = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["workflowState"],
                "issueId": "POI-4966",
                "title": "Invite landing page",
                "changes": {
                    "workflowState": {
                        "old": {"name": "Backlog"},
                        "new": {"name": "toResearch"},
                    }
                },
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Invite landing page")

    def test_returns_none_for_other_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4966",
                "title": "Invite landing page",
            }
        )

        self.assertIsNone(action)

    def test_returns_none_for_non_status_issue_update(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "newStatus": "to research",
                "id": "POI-4966",
                "title": "Invite landing page",
            }
        )

        self.assertIsNone(action)

    def test_returns_none_when_title_already_has_prefix(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4966",
                "title": "cursor researching: Invite landing page",
            }
        )

        self.assertIsNone(action)

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4966",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Invite landing page",
                }
            )
        )

    def test_cli_prints_action_for_matching_event(self):
        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4966",
                    "title": "Invite landing page",
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4966",
                "title": "Cursor researching: Invite landing page",
            },
        )


if __name__ == "__main__":
    unittest.main()
