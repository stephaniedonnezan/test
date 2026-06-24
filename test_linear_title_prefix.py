import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_trigger_context_status_changed_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "To Research",
                    "id": "POI-4788",
                    "title": "Prevent inconsistent timelines for customer events at ingestion time",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4788",
                "title": (
                    "Cursor researching: Prevent inconsistent timelines for customer events "
                    "at ingestion time"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-4788",
                "title": "Prevent inconsistent timelines for customer events at ingestion time",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-1",
            "title": "Research title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_normalizes_casing_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "id": "POI-2",
            "title": "Check normalized status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check normalized status",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "cursor researching: Check duplicate prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_with_updated_state_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4",
                "title": "Nested issue payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5",
                "title": "Description-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_object(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-6",
                "title": "Changed state object",
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed state object",
            },
        )

    def test_requires_issue_identifier_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_identifier_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " POI-8 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-9",
                "title": "CLI smoke",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
