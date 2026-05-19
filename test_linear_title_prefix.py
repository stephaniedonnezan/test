import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_automation_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4718",
                "title": "Log in issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4718",
                "title": "Cursor researching: Log in issue",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Review certificate error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Review certificate error",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4718",
                "title": "Log in issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "Log in issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "cursor researching: Log in issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Investigate login failure",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate login failure",
            },
        )

    def test_prioritizes_explicit_new_status_over_nested_stale_status(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": [{"name": "workflowState"}],
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "id": "abc-123",
                    "title": "Check SSO certificate",
                    "workflowState": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "abc-123",
                "title": "Cursor researching: Check SSO certificate",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "data": {
                "issue": {
                    "id": "POI-3",
                    "title": "Log in issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"})
        )

    def test_cli_prints_json_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "Log in issue",
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
                "issueId": "POI-1",
                "title": "Cursor researching: Log in issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
