import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5039",
            "title": "Default emissions do not trickle down",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Default emissions do not trickle down",
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5040",
                "title": "Investigate title prefixing",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Investigate title prefixing",
            },
        )

    def test_prefixes_nested_linear_state_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5041",
                "title": "Handle Linear webhook state",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Handle Linear webhook state",
            },
        )

    def test_accepts_updated_fields_for_issue_updated_events(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-5042",
                    "title": "Generic update payload",
                    "status": "toResearch",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5042",
                "title": "Cursor researching: Generic update payload",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5043",
            "title": "Comment should not prefix title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5044",
            "title": "Review status should not prefix title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-5045",
            "title": "Title-only update",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5046",
            "title": "cursor researching: Already handled",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5047",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
