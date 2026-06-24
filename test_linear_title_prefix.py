import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload_for_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4079",
            "title": "PoC of error handling pattern",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4079",
                "title": "Cursor researching: PoC of error handling pattern",
            },
        )

    def test_supports_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to_research",
                    "id": "POI-4079",
                    "title": "PoC of error handling pattern",
                },
            }
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-4079")
        self.assertEqual(
            result["title"], "Cursor researching: PoC of error handling pattern"
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4079",
            "title": "PoC of error handling pattern",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4079",
            "title": "PoC of error handling pattern",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "ToResearch",
            "id": "POI-4079",
            "title": "cursor researching: PoC of error handling pattern",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4079",
                    "title": "PoC of error handling pattern",
                    "state": {"name": "To Research"},
                }
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4079",
                "title": "Cursor researching: PoC of error handling pattern",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4079",
                    "title": "PoC of error handling pattern",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_status_from_changes_payload(self):
        event = {
            "action": "issueUpdated",
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "issue": {
                "identifier": "POI-4079",
                "title": "PoC of error handling pattern",
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(
            result["title"], "Cursor researching: PoC of error handling pattern"
        )

    def test_supports_snake_case_updated_field_objects(self):
        event = {
            "action": "update",
            "updated_fields": [{"field": "workflowState"}],
            "issue": {
                "identifier": "POI-4079",
                "title": "PoC of error handling pattern",
                "workflowState": {"name": "To Research"},
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(
            result["title"], "Cursor researching: PoC of error handling pattern"
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "  POI-4079  ",
            "title": "  PoC of error handling pattern  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4079",
                "title": "Cursor researching: PoC of error handling pattern",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "PoC of error handling pattern",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4079",
                }
            )
        )

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4079",
            "title": "PoC of error handling pattern",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4079",
                "title": "Cursor researching: PoC of error handling pattern",
            },
        )


if __name__ == "__main__":
    unittest.main()
