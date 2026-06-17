import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4975",
            "title": "When admin invites user as an Auditor",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: When admin invites user as an Auditor",
            },
        )

    def test_accepts_payload_nested_under_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4975",
                "title": "Auditor role redirects",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Auditor role redirects",
            },
        )

    def test_accepts_issue_update_when_updated_fields_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4975",
                    "title": "Research status title",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Research status title",
            },
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": "state,title",
            "issueId": "POI-4975",
            "title": "Changed through Linear webhook",
            "changes": {"state": {"to": {"name": "ToResearch"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Changed through Linear webhook",
            },
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4975",
            "title": "Unrelated change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4975",
            "title": "Wrong status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4975",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_stdin_json(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4975",
            "title": "CLI sample",
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
                "issueId": "POI-4975",
                "title": "Cursor researching: CLI sample",
            },
        )


if __name__ == "__main__":
    unittest.main()
