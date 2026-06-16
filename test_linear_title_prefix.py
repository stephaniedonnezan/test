import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4999",
            "title": "If no loading event, still show production amount in site view",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": (
                    "Cursor researching: If no loading event, still show production "
                    "amount in site view"
                ),
            },
        )

    def test_prefixes_trigger_context_payload(self):
        event = {
            "automationId": "example",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4999",
                "title": "Mass balance production amount",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: Mass balance production amount",
            },
        )

    def test_prefixes_nested_linear_issue_update_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-value",
                    "identifier": "POI-4999",
                    "title": "Nested issue title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_accepts_camel_case_status_changed_trigger(self):
        event = {
            "webhookType": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-4999",
            "title": "Dashed status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "Cursor researching: Dashed status",
            },
        )

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "newStatus": "to research",
            "id": "POI-4999",
            "title": "Description changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4999",
            "title": "Review title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4999",
            "title": "Comment title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4999",
            "title": "cursor researching: Existing prefix",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4999",
                "title": "cursor researching: Existing prefix",
            },
        )

    def test_requires_issue_identifier_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4999"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_prints_action_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4999",
            "title": "CLI issue",
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
                "issueId": "POI-4999",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
