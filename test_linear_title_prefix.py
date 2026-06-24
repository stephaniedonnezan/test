import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5037",
                "title": "Able to delete supply contracts with connected meter readings",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": (
                    "Cursor researching: Able to delete supply contracts with "
                    "connected meter readings"
                ),
            },
        )

    def test_wrapped_cloud_trigger_context_adds_prefix(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5037",
                    "title": "Able to delete supply contracts with connected meter readings",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": (
                    "Cursor researching: Able to delete supply contracts with "
                    "connected meter readings"
                ),
            },
        )

    def test_status_normalization_accepts_camel_case_trigger_and_separator(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": "POI-1",
                "title": "Investigate inventory gap",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate inventory gap",
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-2",
                "title": "Different status",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "Comment should not update title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_requires_status_field_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "newStatus": "To Research",
            "updatedFields": ["description"],
            "id": "POI-4",
            "title": "Description-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_with_status_field_marker_adds_prefix(self):
        event = {
            "action": "update",
            "type": "Issue",
            "status": "to_research",
            "updatedFields": ["state"],
            "identifier": "POI-5",
            "title": "Needs research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_nested_linear_payload_prefers_issue_identifier_and_title(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "metadata-id",
                "title": "Webhook metadata",
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-6",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_change_mapping_can_supply_new_status(self):
        event = {
            "action": "updated",
            "type": "Issue",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "id": "POI-7",
            "title": "Change object status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Change object status",
        )

    def test_already_prefixed_title_is_ignored_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-8",
                "title": "cursor researching: Already marked",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_identifier_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-9"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_outputs_update_action_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
