import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4983",
            "title": "Importing container events raises export errors",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4983",
                "title": "Cursor researching: Importing container events raises export errors",
            },
        )

    def test_accepts_cursor_trigger_context_wrapper(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4983",
                "title": "Importing container events raises errors",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Importing container events raises errors",
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issue_id": "POI-4983",
            "title": "Research title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title",
        )

    def test_accepts_nested_linear_issue_update_when_status_changed(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4983",
                    "title": "Nested issue",
                    "state": {"name": "To research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4983",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_accepts_changed_status_value(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To research"}},
            "identifier": "POI-4983",
            "title": "Changed status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status",
        )

    def test_change_record_takes_precedence_over_stale_status(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "changes": {"state": {"oldValue": "Backlog", "newValue": "To research"}},
            "status": "Backlog",
            "identifier": "POI-4983",
            "title": "Changed from stale status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed from stale status",
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4983",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4983",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4983",
            "title": "Review status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4983",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4983",
                    "title": " ",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_outputs_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4983",
            "title": "CLI title",
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
                "issueId": "POI-4983",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
