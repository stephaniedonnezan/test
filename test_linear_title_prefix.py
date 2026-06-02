import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_payload_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4169",
            "title": "Export mass balances on Audit is broken when auditing containers",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4169",
                "title": (
                    "Cursor researching: "
                    "Export mass balances on Audit is broken when auditing containers"
                ),
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-1234",
                "title": "Investigate failed export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate failed export",
            },
        )

    def test_accepts_nested_linear_issue_updated_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2345",
                    "title": "Research nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2345",
                "title": "Cursor researching: Research nested payload",
            },
        )

    def test_accepts_camel_case_status_changed_trigger_and_status(self):
        event = {
            "webhookType": "statusChanged",
            "status": "toResearch",
            "issueId": "POI-3456",
            "title": "Normalize status text",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3456",
                "title": "Cursor researching: Normalize status text",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4567",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5678",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-6789",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7890",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8901",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-9012",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9012",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
