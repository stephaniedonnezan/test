import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4765",
            "title": "Remove the fallback",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4765",
                "title": "Cursor researching: Remove the fallback",
            },
        )

    def test_accepts_cursor_automation_trigger_context(self):
        event = {
            "automationId": "automation",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate exporter",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate exporter",
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-id",
                "identifier": "POI-999",
                "title": "Research title automation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-id",
                "title": "Cursor researching: Research title automation",
            },
        )

    def test_ignores_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-123",
            "title": "Investigate exporter",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4765",
            "title": "Remove the fallback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_casing_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-124",
            "title": "Investigate exporter",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate exporter",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4765",
            "title": "cursor researching: Remove the fallback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4765",
            "title": "Remove the fallback",
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
                "issueId": "POI-4765",
                "title": "Cursor researching: Remove the fallback",
            },
        )


if __name__ == "__main__":
    unittest.main()
