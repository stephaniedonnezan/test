import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5034",
                "title": "Supply contracts",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5034",
                "title": "Cursor researching: Supply contracts",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": " POI-1 ",
            "title": "  Map meter inputs  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Map meter inputs",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "issueId": "POI-2",
            "title": "Research later",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-3",
            "title": "Research later",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-4",
            "title": "cursor researching: Supply contracts",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "cursor researching: Supply contracts",
            },
        )

    def test_reads_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_reads_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "changes": {"status": {"from": "Todo", "to": {"name": "to_research"}}},
            "id": "POI-6",
            "title": "Changed status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status",
            },
        )

    def test_reads_status_from_changes_list(self):
        event = {
            "webhookType": "update",
            "changes": [
                {"fieldName": "workflowState", "toValue": {"name": "To Research"}},
            ],
            "key": "POI-7",
            "name": "Workflow state change",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Workflow state change",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-8",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
