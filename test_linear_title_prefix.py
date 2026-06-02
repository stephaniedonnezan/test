import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4754",
            "title": "Cleanup test mock",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )

    def test_prefixes_title_for_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4754",
                "title": "Cleanup test mock",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )

    def test_prefixes_title_for_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-4754",
                    "title": "Cleanup test mock",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4754",
            "title": "Cleanup test mock",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Cleanup test mock",
        )

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4754",
            "title": "Cleanup test mock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4754",
            "title": "Cleanup test mock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4754",
            "title": "cursor researching: Cleanup test mock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No ID"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4754"}
            )
        )


class CliTest(unittest.TestCase):
    def test_cli_outputs_title_update_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4754",
                "title": "Cleanup test mock",
            }
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
                "issueId": "POI-4754",
                "title": "Cursor researching: Cleanup test mock",
            },
        )


if __name__ == "__main__":
    unittest.main()
