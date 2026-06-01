import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_cursor_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3900",
                "title": "Show previous qualified outputs if there are remainings",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3900",
                "title": (
                    "Cursor researching: "
                    "Show previous qualified outputs if there are remainings"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-3900",
                    "title": "Show previous qualified outputs",
                }
            )
        )

    def test_ignores_non_status_change_events(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-3900",
                    "title": "Show previous qualified outputs",
                }
            )
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-3900",
                    "title": "cursor researching: Show previous qualified outputs",
                }
            )
        )

    def test_normalizes_status_and_trigger_spelling(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "issueId": "POI-3900",
                    "title": "Show previous qualified outputs",
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-3900",
                "title": "Cursor researching: Show previous qualified outputs",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-internal-id",
                "identifier": "POI-3900",
                "title": "Show previous qualified outputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3900",
                "title": "Cursor researching: Show previous qualified outputs",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3900",
            "title": "Show previous qualified outputs",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3900",
                "title": "Cursor researching: Show previous qualified outputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
