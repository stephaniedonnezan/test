import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4929",
                "title": "test ticket for bug tracking",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4929",
                "title": "Cursor researching: test ticket for bug tracking",
            },
        )

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "toResearch",
            "issue_id": "POI-123",
            "title": "Research handoff",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research handoff",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4929",
            "title": "test ticket for bug tracking",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4929",
            "title": "test ticket for bug tracking",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4929",
            "title": "cursor researching: test ticket for bug tracking",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4929",
                "title": "cursor researching: test ticket for bug tracking",
            },
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4929",
                    "title": "test ticket for bug tracking",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4929",
                "title": "Cursor researching: test ticket for bug tracking",
            },
        )

    def test_reads_change_new_value_before_current_issue_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "changes": {
                "state": {
                    "oldValue": {"name": "Todo"},
                    "newValue": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-4929",
                    "title": "test ticket for bug tracking",
                    "state": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4929",
                "title": "Cursor researching: test ticket for bug tracking",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4929",
                    "title": "test ticket for bug tracking",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research", "state": {"name": "To Research"}}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4929",
            "title": "test ticket for bug tracking",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4929",
                "title": "Cursor researching: test ticket for bug tracking",
            },
        )


if __name__ == "__main__":
    unittest.main()
