import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_for_to_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_accepts_wrapped_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-5018",
                    "title": "Review proposed GO amount limits",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Review proposed GO amount limits",
            },
        )

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5018",
                    "title": "Error alert with repeating txt",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )

    def test_accepts_status_from_change_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to_research"},
                }
            },
            "issue": {
                "identifier": "POI-5018",
                "title": "Research title automation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Research title automation",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_cursor_researching_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "cursor researching: Error alert with repeating txt",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-5018",
            "title": "Error alert with repeating txt",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert with repeating txt",
            },
        )


if __name__ == "__main__":
    unittest.main()
