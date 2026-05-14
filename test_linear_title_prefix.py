import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4139",
            "title": "Error: can not calculate average on an empty array",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4139",
                "title": "Cursor researching: Error: can not calculate average on an empty array",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4139",
            "title": "Fix dashboard bug",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4139",
            "title": "Fix dashboard bug",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To Research",
            "issueId": "POI-4139",
            "title": "cursor researching: Fix dashboard bug",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_automation_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to-research",
                "title": "Nested issue",
                "id": "POI-1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_accepts_nested_linear_issue_payload_with_state_name(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_requires_updated_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["assignee"],
            "status": "to research",
            "identifier": "POI-3",
            "title": "Assignee changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "status": "toResearch",
            "identifier": "POI-4",
            "title": "Camel case status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Camel case status",
            },
        )

    def test_returns_none_for_missing_title_or_id(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-5"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "No id"})
        )

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "CLI issue",
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
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
