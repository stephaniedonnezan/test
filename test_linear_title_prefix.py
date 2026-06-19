import json
import subprocess
import sys
import unittest

from linear_issue_title import build_issue_title_update as alias_build_issue_title_update
from linear_title_prefix import build_issue_title_update, handleIssueStatusChanged


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "Fix the issue, make the test be green",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Fix the issue, make the test be green",
            },
        )

    def test_accepts_trigger_context_payload_from_automation(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4666",
                "title": "Investigate failing test",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Investigate failing test",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4666",
                    "title": "Research Linear webhook",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Research Linear webhook",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "webhookType": "statusChanged",
            "status": "toResearch",
            "issueId": "POI-4666",
            "title": "Normalize labels",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Normalize labels",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4666",
            "title": "Already fixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_issue_updates_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4666",
            "title": "Title changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "cursor researching: Existing prefix",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "cursor researching: Existing prefix",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_alias_functions_return_same_result(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "Alias coverage",
        }

        self.assertEqual(handleIssueStatusChanged(event), build_issue_title_update(event))
        self.assertEqual(alias_build_issue_title_update(event), build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "CLI coverage",
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
                "issueId": "POI-4666",
                "title": "Cursor researching: CLI coverage",
            },
        )


if __name__ == "__main__":
    unittest.main()
