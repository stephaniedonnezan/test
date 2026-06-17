import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4980",
                "title": "Container traceability",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4980",
                "title": "Cursor researching: Container traceability",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Map evidence",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Map evidence",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4980",
            "title": "Container traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4980",
            "title": "Container traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4980",
            "title": "cursor researching: Container traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Account for inputs",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Account for inputs",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Export audit trail",
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
                "issueId": "POI-3",
                "title": "Cursor researching: Export audit trail",
            },
        )


if __name__ == "__main__":
    unittest.main()
