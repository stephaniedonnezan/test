import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4730",
                "title": "Hide Add Input button in Contianer Allocation tab",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4730",
                "title": "Cursor researching: Hide Add Input button in Contianer Allocation tab",
            },
        )

    def test_status_matching_is_case_separator_and_camel_case_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-4730",
            "title": "Allocate inventory",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allocate inventory",
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4730",
                "title": "Allocate inventory",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4730",
                "title": "Allocate inventory",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4730",
            "title": "cursor researching: Allocate inventory",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_uses_issue_identifier_before_internal_id(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "id": "internal-linear-id",
                    "identifier": "POI-4730",
                    "title": "Allocate inventory",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4730",
                "title": "Cursor researching: Allocate inventory",
            },
        )

    def test_nested_linear_update_accepts_updated_fields(self):
        event = {
            "type": "Issue Updated",
            "updated_fields": ["workflowStateId"],
            "data": {
                "identifier": "POI-4730",
                "title": "Allocate inventory",
                "workflowState": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allocate inventory",
        )

    def test_generic_update_without_status_change_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4730",
                "title": "Allocate inventory",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Allocate inventory",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4730",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_event_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_valid_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4730",
                "title": "Allocate inventory",
            }
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
                "issueId": "POI-4730",
                "title": "Cursor researching: Allocate inventory",
            },
        )


if __name__ == "__main__":
    unittest.main()
