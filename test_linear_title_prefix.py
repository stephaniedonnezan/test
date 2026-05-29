import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4773",
            "title": "CO2 stock",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )

    def test_uses_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4773",
                "title": "CO2 stock",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CO2 stock",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "6f1",
                "title": "Run analysis",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "6f1",
                "title": "Cursor researching: Run analysis",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "webhookType": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1",
            "title": "Investigate",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4773",
            "title": "CO2 stock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4773",
            "title": "CO2 stock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_issue_updated_must_include_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4773",
            "title": "CO2 stock",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4773",
            "title": "cursor researching: CO2 stock",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: CO2 stock",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Untitled",
                }
            )
        )

    def test_cli_prints_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4773",
            "title": "CO2 stock",
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
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )


if __name__ == "__main__":
    unittest.main()
