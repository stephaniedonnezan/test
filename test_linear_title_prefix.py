import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate parser",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate parser",
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "Investigate parser",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_another_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-1",
            "title": "Investigate parser",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "cursor researching: Investigate parser",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identifier_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-1",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Investigate parser",
                }
            )
        )

    def test_supports_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-2",
                    "title": "Research importer behavior",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research importer behavior",
            },
        )

    def test_supports_linear_changes_destination_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Check unit mapping",
                    "state": {"name": "Backlog"},
                },
                "changes": {
                    "workflowState": {
                        "from": {"name": "Backlog"},
                        "to": {"name": "to_research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Check unit mapping",
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-3",
                    "title": "Research importer behavior",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs",
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
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs",
            },
        )


if __name__ == "__main__":
    unittest.main()
