import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4668",
            "title": "Run php UBA excel generate",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4668",
                "title": "Cursor researching: Run php UBA excel generate",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-1234",
                "title": "Investigate report export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate report export",
            },
        )

    def test_accepts_linear_issue_updated_payload_when_status_changed(self):
        event = {
            "action": "Issue Updated",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2000",
                    "title": "Research task",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2000",
                "title": "Cursor researching: Research task",
            },
        )

    def test_normalizes_status_casing_separators_and_camel_case(self):
        event = {
            "webhookType": "statusChanged",
            "new_status": "toResearch",
            "issue_id": "POI-3000",
            "title": "Camel status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel status",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4000",
            "title": "cursor researching: Existing task",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing task",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5000",
            "title": "Comment task",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_without_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-6000",
            "title": "Title-only task",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-7000",
            "title": "Todo task",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-8000"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9000",
            "title": "CLI task",
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
                "issueId": "POI-9000",
                "title": "Cursor researching: CLI task",
            },
        )


if __name__ == "__main__":
    unittest.main()
