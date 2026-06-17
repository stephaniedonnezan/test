import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5008",
            "title": "is the deliveries table discoverable?",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5008",
                "title": "Cursor researching: is the deliveries table discoverable?",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-5008",
                "title": "Research delivery navigation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5008",
                "title": "Cursor researching: Research delivery navigation",
            },
        )

    def test_accepts_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-5008",
                    "title": "Delivery table entry point",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5008",
                "title": "Cursor researching: Delivery table entry point",
            },
        )

    def test_accepts_changed_status_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "to research"}},
            "identifier": "POI-5008",
            "title": "Traceability delivery table",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5008",
                "title": "Cursor researching: Traceability delivery table",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5008",
            "title": "Deliveries",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Deliveries",
        )

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-5008",
            "title": "Deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5008",
            "title": "Deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5008",
            "title": "cursor researching: Deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5008",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Deliveries",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5008",
            "title": "Deliveries",
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
                "issueId": "POI-5008",
                "title": "Cursor researching: Deliveries",
            },
        )


if __name__ == "__main__":
    unittest.main()
