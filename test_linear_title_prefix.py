import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch the meter readings only once",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch the meter readings only once",
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-1234",
                "title": "Investigate meter imports",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate meter imports",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-2222",
            "title": "Handle camel case payloads",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2222",
                "title": "Cursor researching: Handle camel case payloads",
            },
        )

    def test_accepts_nested_linear_issue_status_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3333",
                    "title": "Research nested payloads",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3333",
                "title": "Cursor researching: Research nested payloads",
            },
        )

    def test_extracts_new_status_from_change_record(self):
        event = {
            "type": "Issue",
            "action": "update",
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-4444",
                    "title": "Read change containers",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4444",
                "title": "Cursor researching: Read change containers",
            },
        )

    def test_extracts_new_status_from_updated_fields_objects(self):
        event = {
            "webhookType": "issue.updated",
            "updatedFields": [
                {
                    "field": "workflowState",
                    "newValue": {"name": "To Research"},
                }
            ],
            "issue": {
                "identifier": "POI-5555",
                "title": "Support updated field objects",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5555",
                "title": "Cursor researching: Support updated field objects",
            },
        )

    def test_uses_current_status_when_updated_from_marks_status_change(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "identifier": "POI-6666",
                    "title": "Linear updatedFrom payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6666",
                "title": "Cursor researching: Linear updatedFrom payload",
            },
        )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "issueId": "POI-7777",
            "title": "cursor researching: Existing investigation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7777",
                "title": "cursor researching: Existing investigation",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "issueId": "POI-8888",
            "title": "Finished work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-9999",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "issueId": "POI-1000",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing identifier",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-1001",
                }
            )
        )


class MainTests(unittest.TestCase):
    def test_main_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-1010",
            "title": "CLI event",
        }

        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(output):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-1010",
                "title": "Cursor researching: CLI event",
            },
        )

    def test_main_prints_nothing_when_no_update_needed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "issueId": "POI-1011",
            "title": "CLI no-op",
        }

        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(output):
            self.assertEqual(main(), 0)

        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
