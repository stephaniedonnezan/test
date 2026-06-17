import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "webhookType": "issue",
            "newStatus": "To Research",
            "id": "POI-4998",
            "title": "Why are there four types of events?",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4998",
                "title": "Cursor researching: Why are there four types of events?",
            },
        )

    def test_nested_cursor_trigger_context_payload_adds_prefix(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4998",
                "title": "Why are there four types of events?",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4998",
                "title": "Cursor researching: Why are there four types of events?",
            },
        )

    def test_status_normalization_accepts_camel_case_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "identifier": "POI-1",
            "title": "Research me",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research me",
            },
        )

    def test_nested_linear_issue_update_payload_adds_prefix(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Clarify event types",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Clarify event types",
            },
        )

    def test_change_object_new_value_is_used(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "id": "POI-3",
                "title": "Use change status",
                "status": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Use change status",
            },
        )

    def test_updated_fields_object_new_value_is_used(self):
        event = {
            "action": "update",
            "updatedFields": [
                {
                    "field": "workflowState",
                    "newValue": {"name": "To Research"},
                }
            ],
            "issue": {
                "identifier": "POI-4",
                "title": "Use updated field value",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Use updated field value",
            },
        )

    def test_ignores_current_trigger_status_that_is_not_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4998",
                "title": "Why are there four types of events?",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "Ignore comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-6",
            "title": "Only title changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identifier(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing identifier",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "CLI payload",
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
                "issueId": "POI-9",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
