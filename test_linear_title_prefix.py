import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "[Energy Allocation] GoO Cancelation upload supports more documents",
                "id": "POI-4832",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4832",
                "title": (
                    "Cursor researching: [Energy Allocation] GoO Cancelation upload "
                    "supports more documents"
                ),
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Needs research",
                "id": "POI-1",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Needs research later",
                "id": "POI-2",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "title": "cursor researching: Existing marker",
                "id": "POI-3",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "title": "Camel case status",
                "id": "POI-4",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case status",
        )

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_ignores_nested_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-6",
                    "title": "Description update",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "To Research"}}
            )
        )

    def test_cli_outputs_update_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "title": "CLI payload",
                "id": "POI-7",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )

    def test_cli_exits_without_output_for_non_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "Done",
                "title": "CLI payload",
                "id": "POI-8",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
