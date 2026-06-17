import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4975",
            "title": "Auditor lands on producer view",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Auditor lands on producer view",
            },
        )

    def test_accepts_current_automation_trigger_context_shape(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4975",
                "title": "When admin invites user as an Auditor",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: When admin invites user as an Auditor",
            },
        )

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4975",
                "title": "Auditor does not see audit view",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Auditor does not see audit view",
            },
        )

    def test_reads_new_status_from_change_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "To-Research"}}},
            "data": {
                "issue": {
                    "key": "POI-4975",
                    "title": "Auditor direct URL access",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "Cursor researching: Auditor direct URL access",
            },
        )

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "newStatus": "To Research",
            "identifier": "POI-4975",
            "title": "Description-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "Todo",
            "identifier": "POI-4975",
            "title": "Still todo",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "TO RESEARCH",
            "identifier": "POI-4975",
            "title": "cursor researching: Existing prefix",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4975",
                "title": "cursor researching: Existing prefix",
            },
        )

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4975"}
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4975",
            "title": "CLI payload",
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
                "issueId": "POI-4975",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
