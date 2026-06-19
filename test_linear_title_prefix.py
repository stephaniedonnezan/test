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
                "newStatus": "to research",
                "id": "POI-3945",
                "title": "Deleting a counter reading",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3945",
                "title": "Cursor researching: Deleting a counter reading",
            },
        )

    def test_prefixes_case_insensitive_status_with_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "issueId": "POI-2",
            "title": "Fix thing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-3",
            "title": "Fix thing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4",
            "title": "cursor researching: Fix thing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-id",
                "identifier": "POI-5",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_prefixes_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "data": {"issue": {"identifier": "POI-6", "title": "Changed status"}},
            "changes": {"status": {"newValue": "to_research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-7",
                    "title": "Renamed issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3945",
                "title": "Deleting a counter reading",
            }
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
                "issueId": "POI-3945",
                "title": "Cursor researching: Deleting a counter reading",
            },
        )


if __name__ == "__main__":
    unittest.main()
