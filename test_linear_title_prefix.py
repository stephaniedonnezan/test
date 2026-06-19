import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_full_automation_payload_uses_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "statusChanged",
                    "newStatus": "to-research",
                    "id": "POI-4969",
                    "title": "Unexpected star icon when linking deliveries",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_nested_linear_status_update_uses_issue_identifier(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"state": {"name": "Backlog"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_nested_linear_issue_payload_under_data_issue(self):
        event = {
            "type": "issue.updated",
            "changedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4969",
                    "title": "Unexpected star icon when linking deliveries",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_skips_non_research_status(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_generic_update_without_status_changed_field(self):
        event = {
            "type": "issue.updated",
            "changedFields": ["title"],
            "data": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4969",
            "title": "cursor researching: Unexpected star icon when linking deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_issue_id_or_title_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerType": "status_changed",
                    "newStatus": "To Research",
                    "title": "Unexpected star icon when linking deliveries",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerType": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4969",
                }
            )
        )

    def test_cli_reads_json_from_stdin_and_prints_update(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
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
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )


if __name__ == "__main__":
    unittest.main()
