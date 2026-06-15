import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4937",
            "title": "Error: Unit kg is not supported for Electricity",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_accepts_cursor_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4937",
                "title": "Investigate electricity unit support",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Investigate electricity unit support",
            },
        )

    def test_normalizes_camel_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4937",
            "title": "Research status title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research status title",
        )

    def test_returns_none_for_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4937",
            "title": "Error: Unit kg is not supported for Electricity",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4937",
            "title": "Research status title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4937",
            "title": "cursor researching: Research status title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4937",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4937",
                    "title": "Changes payload",
                }
            },
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changes payload",
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4937",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4937",
            "title": "CLI payload",
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
                "issueId": "POI-4937",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
