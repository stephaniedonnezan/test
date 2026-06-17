import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4965",
                "title": "performance: fetch meter readings once",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_cursor_researching_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_RESEARCH",
            "id": "POI-4965",
            "title": "cursor researching: performance: fetch meter readings once",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "cursor researching: performance: fetch meter readings once",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "performance: fetch meter readings once",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_handles_changes_payload_for_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "performance: fetch meter readings once",
                }
            },
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_ignores_generic_updates_without_status_change_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4965"}
            )
        )

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )


if __name__ == "__main__":
    unittest.main()
