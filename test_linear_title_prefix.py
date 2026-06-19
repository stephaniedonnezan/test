import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_current_cursor_to_research_payload(self):
        payload = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4971",
                    "title": "E-mail verification after account setup",
                    "status": "To Research",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4971",
                "title": "Cursor researching: E-mail verification after account setup",
            },
        )

    def test_supports_flat_trigger_context_payload(self):
        payload = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": " POI-123 ",
            "title": "  Investigate onboarding redirect ",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate onboarding redirect",
            },
        )

    def test_supports_nested_linear_update_payload_with_updated_fields(self):
        payload = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Review confirmation email",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Review confirmation email",
            },
        )

    def test_supports_linear_changes_object(self):
        payload = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "poi-789",
                    "title": "Normalize status webhook handling",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "poi-789",
                "title": "Cursor researching: Normalize status webhook handling",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        payload = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Comment should not rename issue",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_different_status(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-123",
            "title": "Only research transitions are renamed",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_generic_update_without_status_field(self):
        payload = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-123",
            "title": "Title-only update should not loop",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "cursor researching: Already handled",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_missing_issue_id(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_missing_title(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-321",
            "title": "CLI payload",
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
                "issueId": "POI-321",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
