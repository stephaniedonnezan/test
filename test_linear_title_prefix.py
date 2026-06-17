import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5016",
                "title": "Add Input Country of origin UX to review",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5016",
                "title": "Cursor researching: Add Input Country of origin UX to review",
            },
        )

    def test_prefixes_direct_flat_status_change_to_research(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-5016",
            "title": "Review input labels",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5016",
                "title": "Cursor researching: Review input labels",
            },
        )

    def test_prefixes_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5016",
                    "title": "Review input labels",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5016",
                "title": "Cursor researching: Review input labels",
            },
        )

    def test_uses_changed_status_value_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "id": "POI-5016",
                    "title": "Review input labels",
                }
            },
            "changes": {"state": {"from": "Backlog", "to": "to-research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5016",
                "title": "Cursor researching: Review input labels",
            },
        )

    def test_ignores_non_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5016",
            "title": "Review input labels",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-5016",
            "title": "Review input labels",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5016",
            "title": "cursor researching: Review input labels",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payloads_without_issue_identity(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Review input labels",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "id": "POI-5016",
            "title": "Review input labels",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5016",
                "title": "Cursor researching: Review input labels",
            },
        )


if __name__ == "__main__":
    unittest.main()
