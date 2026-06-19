import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_cursor_status_changed_to_research_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_trigger_context_payload_adds_prefix(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4961",
                "title": "Remove Subscribe button on invite",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_nested_linear_update_payload_uses_issue_identifier(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4961",
                    "title": "Remove Subscribe button on invite",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_changed_status_object_adds_prefix(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4961",
                    "title": "Remove Subscribe button on invite",
                }
            },
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "to_research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_status_normalization_accepts_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
            "title": "cursor researching: Remove Subscribe button on invite",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_other_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_update_is_ignored(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4961",
                    "title": "Remove Subscribe button on invite",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
        }

        self.assertIsNone(build_issue_title_update(event))


class CliTests(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4961",
                "title": "Remove Subscribe button on invite",
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
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )


if __name__ == "__main__":
    unittest.main()
