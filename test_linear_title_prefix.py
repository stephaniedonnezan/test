import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4898",
            "title": "Duplicate meter reading found",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_accepts_nested_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_accepts_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4898",
                    "title": "Duplicate meter reading found",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_accepts_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "ToResearch"}},
            "issueId": "POI-4898",
            "title": "Duplicate meter reading found",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4898",
            "title": "Duplicate meter reading found",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4898",
            "title": "Duplicate meter reading found",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4898",
            "title": "cursor researching: Duplicate meter reading found",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_data(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Duplicate meter reading found",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4898",
            "title": "Duplicate meter reading found",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )


if __name__ == "__main__":
    unittest.main()
