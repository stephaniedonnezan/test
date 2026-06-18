import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5069",
                "title": "Add avoided CO2 emissions KPI",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5069",
                "title": "Cursor researching: Add avoided CO2 emissions KPI",
            },
        )

    def test_accepts_context_directly(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Research this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research this",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-2",
                "title": "Todo issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "Commented issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_accepts_linear_data_as_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "id": "issue-uuid",
                "title": "Data payload issue",
                "workflowState": {"name": "to-research"},
            },
            "updatedFields": ["workflowState"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Data payload issue",
            },
        )

    def test_uses_changed_status_value_for_generic_update(self):
        event = {
            "action": "updated",
            "changes": {"status": {"from": "Todo", "to": "ToResearch"}},
            "data": {"identifier": "POI-6", "title": "Changed status issue"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status issue",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-7",
                "title": "Title only",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_required_issue_data(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research"}
            )
        )

    def test_cli_reads_json_and_writes_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-8",
                "title": "CLI issue",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
