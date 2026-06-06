import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_to_research_returns_update(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4839",
                "title": "UBA POS: version number is not incremented when there is an intermediate",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4839",
                "title": "Cursor researching: UBA POS: version number is not incremented when there is an intermediate",
            },
        )

    def test_current_in_review_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4839",
                "title": "UBA POS: version number is not incremented when there is an intermediate",
                "status": "In Review",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-1",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-2",
            "title": "Ignored issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_name_is_normalized(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-3",
            "title": "Normalized issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Normalized issue",
            },
        )

    def test_status_changed_can_fallback_to_current_status(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "id": "POI-4",
            "title": "Fallback status issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Fallback status issue",
            },
        )

    def test_nested_linear_update_uses_nested_issue_identity(self):
        event = {
            "id": "webhook-delivery-id",
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "issue-record-id",
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

    def test_generic_update_without_status_change_metadata_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "status": "To Research",
            "id": "POI-6",
            "title": "Priority update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_change_metadata_can_supply_new_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "issue": {
                "identifier": "POI-7",
                "title": "Workflow update",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Workflow update",
            },
        )

    def test_missing_identity_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-8"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Untitled"}
            )
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class CommandLineTest(unittest.TestCase):
    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: CLI issue",
            },
        )
        self.assertEqual(result.stderr, "")

    def test_cli_exits_one_without_output_for_non_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-10",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
