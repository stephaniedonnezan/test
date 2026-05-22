import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4311",
            "title": "Downstream emissions dialog refinment",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4311",
                "title": "Cursor researching: Downstream emissions dialog refinment",
            },
        )

    def test_builds_update_from_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-1",
                "title": "Investigate battery behavior",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate battery behavior",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4311",
            "title": "Downstream emissions dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4311",
            "title": "Downstream emissions dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4311",
            "title": "cursor researching: Downstream emissions dialog refinment",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "identifier": "POI-2",
            "title": "Check charger telemetry",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check charger telemetry",
            },
        )

    def test_supports_linear_issue_updated_payload_with_changed_status(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "identifier": "POI-3",
                "title": "Research inverter allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research inverter allocation",
            },
        )

    def test_ignores_linear_issue_updated_payload_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-id",
                "title": "Research inverter allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prioritizes_explicit_new_status_over_nested_stale_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "POI-4",
                    "title": "Inspect forecast inputs",
                    "status": "Backlog",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Inspect forecast inputs",
            },
        )

    def test_returns_none_when_issue_id_or_title_is_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_prints_update_action_for_json_stdin(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-6",
                    "title": "Map research workflow",
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Map research workflow",
            },
        )


if __name__ == "__main__":
    unittest.main()
