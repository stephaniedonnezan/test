import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3907",
            "title": "fully review all the values in the transport e2e",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3907",
                "title": "Cursor researching: fully review all the values in the transport e2e",
            },
        )

    def test_accepts_nested_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "id": "issue-1",
                "title": "Investigate emissions numbers",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-1",
                "title": "Cursor researching: Investigate emissions numbers",
            },
        )

    def test_accepts_linear_issue_updated_payload_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "identifier": "POI-123",
                "title": "Check transport values",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Check transport values",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3907",
            "title": "fully review all the values in the transport e2e",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3907",
            "title": "fully review all the values in the transport e2e",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-3907",
            "title": "fully review all the values in the transport e2e",
            "state": {"name": "To Research"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3907",
            "title": "cursor researching: fully review all the values in the transport e2e",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3907",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3907",
            "title": "Review transport e2e values",
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
                "issueId": "POI-3907",
                "title": "Cursor researching: Review transport e2e values",
            },
        )


if __name__ == "__main__":
    unittest.main()
