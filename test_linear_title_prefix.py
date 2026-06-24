import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_for_to_research_status(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "cursor researching: Duplicate meter reading found",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Duplicate meter reading found",
        )

    def test_supports_generic_issue_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4898",
                "title": "Duplicate meter reading found",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4898",
                "title": "Duplicate meter reading found",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_linear_updated_from_state_id_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "identifier": "POI-4898",
                    "title": "Duplicate meter reading found",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4898",
        )

    def test_supports_workflow_state_status_name(self):
        event = {
            "triggerContext": {
                "trigger": "workflow_state_changed",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Duplicate meter reading found",
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4898 ",
                "title": " Duplicate meter reading found ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Duplicate meter reading found",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_from_stdin_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4898",
                "title": "Duplicate meter reading found",
            },
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
                "issueId": "POI-4898",
                "title": "Cursor researching: Duplicate meter reading found",
            },
        )


if __name__ == "__main__":
    unittest.main()
