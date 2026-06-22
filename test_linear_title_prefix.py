import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4047",
                "title": "Date picker requires multiple clicks",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4047",
                "title": "Cursor researching: Date picker requires multiple clicks",
            },
        )

    def test_uses_top_level_values_from_cursor_trigger_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-1",
            "title": "Investigate flaky report",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate flaky report",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-2",
                    "title": "Research onboarding flow",
                    "state": {"name": "to_research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research onboarding flow",
            },
        )

    def test_accepts_changed_status_value_from_changes(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "changes": {
                "workflowState": {
                    "oldValue": "Backlog",
                    "newValue": {"name": "to-research"},
                }
            },
            "id": "POI-3",
            "title": "Normalize energy metrics",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Normalize energy metrics",
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-4047",
            "title": "Date picker requires multiple clicks",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4",
            "title": "New title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Add comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "cursor researching: Existing work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
                }
            )
        )

    def test_cli_prints_matching_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "CLI smoke test",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
