import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3878",
            "title": "CO2 inputs missing from November mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3878",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )

    def test_accepts_cursor_automation_trigger_context_shape(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "CO2 inputs missing from November mass balance",
                "id": "POI-3878",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3878",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )

    def test_accepts_linear_issue_update_with_state_field_change(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "updatedFields": ["state"],
                "state": {"name": "to-research"},
                "issue": {
                    "id": "linear-issue-id",
                    "identifier": "POI-3878",
                    "title": "CO2 inputs missing from November mass balance",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )

    def test_accepts_changed_status_payload(self):
        event = {
            "action": "update",
            "changes": [
                {
                    "field": "workflowState",
                    "to": {"name": "toResearch"},
                }
            ],
            "issue": {
                "identifier": "POI-3878",
                "title": "CO2 inputs missing from November mass balance",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3878",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )

    def test_accepts_mapped_changed_status_payload(self):
        event = {
            "action": "update",
            "changes": {"state": {"to": {"name": "To Research"}}},
            "issue": {
                "identifier": "POI-3878",
                "title": "CO2 inputs missing from November mass balance",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3878",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-3878",
            "title": "CO2 inputs missing from November mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CO2 inputs missing from November mass balance",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-3878",
            "title": "CO2 inputs missing from November mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3878",
            "title": "CO2 inputs missing from November mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3878",
            "title": "cursor researching: CO2 inputs missing from November mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "CO2 inputs missing from November mass balance",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3878"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


class CliTest(unittest.TestCase):
    def test_cli_reads_json_from_stdin(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3878",
            "title": "CO2 inputs missing from November mass balance",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3878",
                "title": "Cursor researching: CO2 inputs missing from November mass balance",
            },
        )


if __name__ == "__main__":
    unittest.main()
