import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_trigger_entering_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4993",
            "title": "Should the site card contain the button to site settings ?",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4993",
                "title": (
                    "Cursor researching: "
                    "Should the site card contain the button to site settings ?"
                ),
            },
        )

    def test_accepts_cursor_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4993",
                "title": "Update site settings entry point",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4993",
                "title": "Cursor researching: Update site settings entry point",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4993",
            "title": "Update site settings entry point",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4993",
            "title": "Update site settings entry point",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4993",
            "title": "cursor researching: Update site settings entry point",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "9b140cd2-42ca-4db0-ba61-ba6e29377b0c",
                    "identifier": "POI-4993",
                    "title": "Update site settings entry point",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4993",
                "title": "Cursor researching: Update site settings entry point",
            },
        )

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4993",
                    "title": "Update site settings entry point",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "oldValue": "Backlog",
                    "newValue": "toResearch",
                }
            },
            "issue": {
                "identifier": "POI-4993",
                "title": "Update site settings entry point",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4993",
                "title": "Cursor researching: Update site settings entry point",
            },
        )

    def test_cli_prints_update_action_for_json_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4993",
            "title": "Update site settings entry point",
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
                "issueId": "POI-4993",
                "title": "Cursor researching: Update site settings entry point",
            },
        )


if __name__ == "__main__":
    unittest.main()
