import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_for_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5004",
                "title": "Search is not filtering all content",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5004",
                "title": "Search is not filtering all content",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5004",
                "title": "Search is not filtering all content",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "identifier": "POI-5004",
            "title": "cursor researching: Search is not filtering all content",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_case_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "ToResearch",
            "issue_id": "POI-5004",
            "title": "Search is not filtering all content",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5004",
                "title": "Search is not filtering all content",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_supports_nested_issue_under_data(self):
        event = {
            "trigger": "issue_updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "POI-5004",
                    "title": "Search is not filtering all content",
                    "workflowState": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_supports_change_object_new_status(self):
        event = {
            "action": "updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "key": "POI-5004",
            "title": "Search is not filtering all content",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Search is not filtering all content",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5004",
            "title": "Search is not filtering all content",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5004",
                "title": "Cursor researching: Search is not filtering all content",
            },
        )

    def test_cli_prints_nothing_for_noop(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "done",
            "id": "POI-5004",
            "title": "Search is not filtering all content",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
