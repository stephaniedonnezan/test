import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "webhookType": "issue",
            "newStatus": "To Research",
            "id": "POI-2642",
            "title": "[1250]Guarantee of origin upload: improve UX",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2642",
                "title": "Cursor researching: [1250]Guarantee of origin upload: improve UX",
            },
        )

    def test_supports_trigger_context_payloads(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to_research",
                "id": "POI-1",
                "title": "Investigate imports",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate imports",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-2",
            "title": "Ready for testing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "id": "webhook-event-id",
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_supports_changed_status_metadata(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "to-research"}},
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Changed status metadata",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status metadata",
            },
        )

    def test_returns_none_for_incomplete_payloads(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-7",
            "title": "CLI sample",
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI sample",
            },
        )


if __name__ == "__main__":
    unittest.main()
