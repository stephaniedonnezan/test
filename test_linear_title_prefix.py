import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_to_research_status(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "oldStatus": "Backlog",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4878",
                "title": "Cursor researching: LPH enablement even if no BOP",
            },
        )

    def test_full_automation_payload(self):
        payload = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "oldStatus": "Todo",
                "id": "POI-1",
                "title": "Investigate allocation behavior",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate allocation behavior",
            },
        )

    def test_does_not_match_other_statuses(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "Done",
            "oldStatus": "To Research",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_requires_status_change(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "title_changed",
            "newStatus": "to research",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_preserves_existing_cursor_researching_prefix(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "oldStatus": "Todo",
            "id": "POI-4878",
            "title": "cursor researching: LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_nested_linear_webhook_payload(self):
        payload = {
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4878",
                "title": "LPH enablement even if no BOP",
                "state": {"name": "TO_RESEARCH"},
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4878",
                "title": "Cursor researching: LPH enablement even if no BOP",
            },
        )

    def test_nested_linear_changes_payload(self):
        payload = {
            "type": "Issue",
            "changes": {"state": {"from": "Todo", "to": {"name": "To Research"}}},
            "issue": {
                "id": "linear-uuid",
                "title": "Research metering setup",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Research metering setup",
            },
        )

    def test_missing_issue_title_is_ignored(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "oldStatus": "Todo",
            "id": "POI-4878",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_non_linear_event_is_ignored(self):
        payload = {
            "triggerType": "github",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "oldStatus": "Todo",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_cli_prints_update_for_matching_payload(self):
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "oldStatus": "Todo",
            "id": "POI-4878",
            "title": "LPH enablement even if no BOP",
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
                "issueId": "POI-4878",
                "title": "Cursor researching: LPH enablement even if no BOP",
            },
        )


if __name__ == "__main__":
    unittest.main()
