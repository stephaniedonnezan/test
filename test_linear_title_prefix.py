import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_linear_automation_status_change(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Fix allocation bug",
                "id": "POI-4682",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4682",
                "title": "Cursor researching: Fix allocation bug",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "title": "Investigate issue",
            "issueId": "POI-1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_accepts_nested_issue_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "type": "Issue",
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "title": "Fix allocation bug",
            "id": "POI-4682",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "title": "Fix allocation bug",
            "id": "POI-4682",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_when_updated_fields_do_not_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "title": "Fix allocation bug",
            "id": "POI-4682",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "cursor researching: Fix allocation bug",
            "id": "POI-4682",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title_and_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Fix allocation bug",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4682",
                }
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Fix allocation bug",
            "id": "POI-4682",
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
                "issueId": "POI-4682",
                "title": "Cursor researching: Fix allocation bug",
            },
        )


if __name__ == "__main__":
    unittest.main()
