import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_gets_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4974",
            "title": "User removal flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_cursor_trigger_context_payload_is_supported(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4974",
                "title": "User removal flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_nested_linear_status_changed_payload_is_supported(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4974",
                    "title": "User removal flow",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_change_record_can_provide_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": [
                {"field": "workflowState", "newValue": {"name": "to_research"}},
            ],
            "issue": {
                "key": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_case_and_separator_variants_are_normalized(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO-RESEARCH",
            "issueId": "POI-4974",
            "title": "User removal flow",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User removal flow",
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4974",
            "title": "User removal flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_update_without_status_field_change_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4974",
                    "title": "User removal flow",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_cursor_researching_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4974",
            "title": "cursor researching: User removal flow",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4974",
            "title": "User removal flow",
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
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )


if __name__ == "__main__":
    unittest.main()
