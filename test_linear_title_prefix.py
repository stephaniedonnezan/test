import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4992",
                "title": "Not all container events are displayed by default",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4992",
                "title": "Cursor researching: Not all container events are displayed by default",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4992",
                "title": "Not all container events are displayed by default",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4992",
            "title": "Not all container events are displayed by default",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4992",
            "title": "cursor researching: Not all container events are displayed by default",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4992",
                "title": "cursor researching: Not all container events are displayed by default",
            },
        )

    def test_normalizes_status_casing_separators_and_camel_case_trigger(self):
        event = {
            "trigger": "workflowStateChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-4992",
            "title": "Not all container events are displayed by default",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Not all container events are displayed by default",
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4992",
                    "title": "Not all container events are displayed by default",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4992",
                "title": "Cursor researching: Not all container events are displayed by default",
            },
        )

    def test_reads_new_status_from_change_metadata(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Todo", "newValue": "to research"}},
            "identifier": "POI-4992",
            "title": "Not all container events are displayed by default",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Not all container events are displayed by default",
        )

    def test_missing_issue_identifier_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4992",
            "title": "Not all container events are displayed by default",
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
                "issueId": "POI-4992",
                "title": "Cursor researching: Not all container events are displayed by default",
            },
        )


if __name__ == "__main__":
    unittest.main()
