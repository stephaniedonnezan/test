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
            "id": "POI-4625",
            "title": "Potential bug / logic error - delivery ID 7937",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: Potential bug / logic error - delivery ID 7937",
            },
        )

    def test_prefixes_nested_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4625",
                "title": "Investigate RFNBO content",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: Investigate RFNBO content",
            },
        )

    def test_prefixes_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4625",
                    "title": "Nested issue",
                    "state": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4625",
            "title": "Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4625",
            "title": "Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4625",
            "title": "Issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4625",
            "title": "cursor researching: Existing prefix",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "cursor researching: Existing prefix",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4625",
            "title": "CLI issue",
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
                "issueId": "POI-4625",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
