import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4110",
            "title": "Seeder helper tool",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4110",
                "title": "Cursor researching: Seeder helper tool",
            },
        )

    def test_accepts_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4110",
                    "title": "Seeder helper tool",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Seeder helper tool",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4110",
            "title": "Seeder helper tool",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4110",
            "title": "Seeder helper tool",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4110",
            "title": "cursor researching: Seeder helper tool",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4110",
            "title": "Seeder helper tool",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Seeder helper tool",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4110",
                "title": "Seeder helper tool",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Seeder helper tool",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4110",
                "title": "Seeder helper tool",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_extracts_new_status_from_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"state": {"from": "Todo", "to": "To Research"}},
            "data": {"id": "POI-4110", "title": "Seeder helper tool"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Seeder helper tool",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4110 ",
            "title": "  Seeder helper tool  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4110",
                "title": "Cursor researching: Seeder helper tool",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4110"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Seeder helper tool"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4110",
            "title": "Seeder helper tool",
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
                "issueId": "POI-4110",
                "title": "Cursor researching: Seeder helper tool",
            },
        )


if __name__ == "__main__":
    unittest.main()
