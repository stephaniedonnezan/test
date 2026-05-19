import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4671",
            "title": "Bug: over allocation of ppa throws 500",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4671",
                "title": "Cursor researching: Bug: over allocation of ppa throws 500",
            },
        )

    def test_prefixes_title_for_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4671",
                "title": "Investigate allocation error",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4671",
                "title": "Cursor researching: Investigate allocation error",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4671",
            "title": "Bug: over allocation of ppa throws 500",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4671",
            "title": "Bug: over allocation of ppa throws 500",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4671",
            "title": "cursor researching: Bug: over allocation of ppa throws 500",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFrom": {"stateId": "old-state-id"},
                "issue": {
                    "identifier": "POI-4671",
                    "title": "Bug: over allocation of ppa throws 500",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4671",
                "title": "Cursor researching: Bug: over allocation of ppa throws 500",
            },
        )

    def test_accepts_issue_updated_with_updated_fields(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "issue": {
                "issueId": "POI-4671",
                "title": "Investigate allocation error",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4671",
                "title": "Cursor researching: Investigate allocation error",
            },
        )

    def test_ignores_generic_update_when_status_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "issue": {
                "id": "POI-4671",
                "title": "Investigate allocation error",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4671",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4671",
            "title": "Investigate allocation error",
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
                "issueId": "POI-4671",
                "title": "Cursor researching: Investigate allocation error",
            },
        )


if __name__ == "__main__":
    unittest.main()
