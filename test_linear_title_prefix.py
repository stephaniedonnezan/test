import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_uses_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-123",
                "title": "Investigate issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Check methane seeder",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Check methane seeder",
            },
        )

    def test_supports_workflow_state_status(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Research issue",
                    "workflowState": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-456",
            "title": "Research camel case",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research camel case",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Check methane seeder",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "cursor researching: Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "No issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4658",
                    "title": "   ",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4658",
                "title": "Tidy up turn/ch4 seeders",
            }
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )


if __name__ == "__main__":
    unittest.main()
