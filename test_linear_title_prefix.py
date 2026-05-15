import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4347",
                "title": "Fix duplicate meter readings",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4347",
                "title": "Cursor researching: Fix duplicate meter readings",
            },
        )

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4347",
                "title": "Fix duplicate meter readings",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_trigger(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4347",
                "title": "Fix duplicate meter readings",
            }
        )

        self.assertIsNone(update)

    def test_avoids_duplicate_prefix_case_insensitively(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "id": "POI-4347",
                "title": "cursor researching: Fix duplicate meter readings",
            }
        )

        self.assertIsNone(update)

    def test_normalizes_status_variants(self):
        update = build_issue_title_update(
            {
                "trigger": "status-changed",
                "newStatus": "to_research",
                "issueId": "POI-4347",
                "title": "Fix duplicate meter readings",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Fix duplicate meter readings")

    def test_accepts_nested_cursor_trigger_context(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4347",
                    "title": "Fix duplicate meter readings",
                }
            }
        )

        self.assertEqual(update["issueId"], "POI-4347")
        self.assertEqual(update["title"], "Cursor researching: Fix duplicate meter readings")

    def test_accepts_linear_issue_updated_payload_when_status_changed(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "id": "issue-id",
                    "title": "Fix duplicate meter readings",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "issue-id")
        self.assertEqual(update["title"], "Cursor researching: Fix duplicate meter readings")

    def test_ignores_linear_issue_updated_payload_without_status_change(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "id": "issue-id",
                    "title": "Fix duplicate meter readings",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(update)

    def test_missing_issue_identity_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Fix duplicate meter readings",
                }
            )
        )

        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4347",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4347",
            "title": "Fix duplicate meter readings",
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
                "issueId": "POI-4347",
                "title": "Cursor researching: Fix duplicate meter readings",
            },
        )


if __name__ == "__main__":
    unittest.main()
