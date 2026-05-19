import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_cursor_status_changed_trigger(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_cursor_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-123",
                "identifier": "POI-4483",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_nested_issue_object(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "issue-123",
                    "title": "Gather ETS daily prices",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_status_name_object(self):
        event = {
            "trigger": "statusChanged",
            "status": {"name": "to_research"},
            "issueId": "issue-123",
            "title": "Gather ETS daily prices",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_matches_status_case_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather ETS daily prices",
        )

    def test_explicit_new_status_takes_priority_over_nested_stale_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "status": "In Review",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather ETS daily prices",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_when_changed_fields_exclude_status(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "cursor researching: Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4483"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Gather ETS daily prices",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
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
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
