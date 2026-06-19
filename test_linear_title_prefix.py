import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4619",
            "title": "Adjust global UI button",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4619",
                "title": "Cursor researching: Adjust global UI button",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issue_id": "POI-1",
            "title": "Investigate pricing",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate pricing",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4619",
            "title": "Adjust global UI button",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4619",
            "title": "Adjust global UI button",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4619",
            "title": "cursor researching: Adjust global UI button",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-4619",
                    "title": "Adjust global UI button",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4619",
                "title": "Cursor researching: Adjust global UI button",
            },
        )

    def test_prefers_changed_status_over_current_status(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "status": "Backlog",
            "identifier": "POI-2",
            "title": "Research status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research status",
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4619",
                "title": "Adjust global UI button",
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
                "issueId": "POI-4619",
                "title": "Cursor researching: Adjust global UI button",
            },
        )


if __name__ == "__main__":
    unittest.main()
