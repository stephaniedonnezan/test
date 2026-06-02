import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4774",
            "title": "Misrepresentation of CO2 stock in mass balance export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: "
                    "Misrepresentation of CO2 stock in mass balance export"
                ),
            },
        )

    def test_accepts_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4774",
                "title": "Misrepresentation of CO2 stock in mass balance export",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: "
                    "Misrepresentation of CO2 stock in mass balance export"
                ),
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4774",
                "title": "Misrepresentation of CO2 stock in mass balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: "
                    "Misrepresentation of CO2 stock in mass balance export"
                ),
            },
        )

    def test_accepts_nested_issue_when_envelope_has_its_own_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Research title update",
                    "workflowState": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Research title update",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4774",
            "title": "Research title update",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": "Cursor researching: Research title update",
            },
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": "Research title update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4774",
            "title": "Research title update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4774",
                "title": "Research title update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": "cursor researching: Research title update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))

    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": "Research title update",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": "Cursor researching: Research title update",
            },
        )


if __name__ == "__main__":
    unittest.main()
