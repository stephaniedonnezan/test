import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_status_changed_trigger(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3582",
            "title": "Customer satisfaction survey",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3582",
                "title": "Cursor researching: Customer satisfaction survey",
            },
        )

    def test_adds_prefix_for_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3582",
                "title": "Customer satisfaction survey",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3582",
                "title": "Cursor researching: Customer satisfaction survey",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-3582",
                "title": "Customer satisfaction survey",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Customer satisfaction survey",
            },
        )

    def test_status_matching_is_case_separator_and_camel_case_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To-Research",
            "issueId": "POI-3582",
            "title": "Customer satisfaction survey",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3582",
                "title": "Cursor researching: Customer satisfaction survey",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3582",
            "title": "cursor researching: Customer satisfaction survey",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3582",
            "title": "Customer satisfaction survey",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-3582",
                "title": "Customer satisfaction survey",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3582",
            "title": "Customer satisfaction survey",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-3582"})
        )

    def test_cli_prints_action_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3582",
            "title": "Customer satisfaction survey",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3582",
                "title": "Cursor researching: Customer satisfaction survey",
            },
        )


if __name__ == "__main__":
    unittest.main()
