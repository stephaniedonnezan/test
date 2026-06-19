import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4049",
                "title": "The audit tables randomly resize",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4049",
                "title": "Cursor researching: The audit tables randomly resize",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-1",
                "title": "Investigate export behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export behavior",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-2",
                "title": "Keep original title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Keep original title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "cursor researching: Already queued",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_current_state(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "identifier": "POI-5",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_nested_linear_change_value_can_supply_new_status(self):
        event = {
            "webhookType": "Issue",
            "action": "update",
            "data": {
                "changes": {
                    "workflowState": {
                        "oldValue": {"name": "Backlog"},
                        "newValue": {"name": "to research"},
                    }
                },
                "issue": {
                    "identifier": "POI-6",
                    "title": "Workflow state payload",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Workflow state payload",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-7",
                    "title": "Description changed",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-8"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "No id",
                }
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-9",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
