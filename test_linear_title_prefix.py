import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4123",
                "title": "Add a site switch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4123",
                "title": "Cursor researching: Add a site switch",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1",
            "title": "Review payment flows",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Review payment flows",
            },
        )

    def test_accepts_status_with_separators(self):
        event = {
            "trigger": "issue_status_changed",
            "new_status": "to-research",
            "identifier": "POI-2",
            "title": "Investigate site switcher",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate site switcher",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3",
            "title": "Add analytics",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "Add comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "cursor researching: Add exports",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_generic_linear_update_with_changed_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["status"],
            "data": {
                "identifier": "POI-6",
                "title": "Build forecast page",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Build forecast page",
            },
        )

    def test_generic_update_requires_changed_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-7",
                "title": "Rename dashboard",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "updated",
            "type": "Issue",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-8",
                    "title": "Assess workflow states",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Assess workflow states",
            },
        )

    def test_prefers_nested_issue_identifier_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-9",
                    "title": "Use nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Use nested issue",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-10"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-11",
            "title": "Run from stdin",
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
                "issueId": "POI-11",
                "title": "Cursor researching: Run from stdin",
            },
        )


if __name__ == "__main__":
    unittest.main()
