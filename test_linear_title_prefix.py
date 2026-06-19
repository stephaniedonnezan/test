import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4042",
                "title": "Solve the flake",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4042",
                "title": "Cursor researching: Solve the flake",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-123",
            "title": "Investigate API regression",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate API regression",
        )

    def test_ignores_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "issueId": "POI-123",
            "title": "Implement feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-123",
            "title": "Research task",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-123",
            "title": "cursor researching: Existing title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing title",
        )

    def test_handles_nested_linear_update_payload_with_changes(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Understand flaky Cypress test",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {
                "status": {
                    "oldValue": "Backlog",
                    "newValue": "To Research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Understand flaky Cypress test",
            },
        )

    def test_handles_generic_update_when_updated_fields_mentions_state(self):
        event = {
            "webhookType": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-789",
                    "title": "Audit flaky test logs",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Audit flaky test logs",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-123",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "identifier": "POI-321",
            "title": "Review flaky tests",
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
                "title": "Cursor researching: Review flaky tests",
            },
        )


if __name__ == "__main__":
    unittest.main()
