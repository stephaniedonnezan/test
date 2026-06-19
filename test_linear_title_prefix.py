import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4890",
                "title": "Create",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4890",
                "title": "Cursor researching: Create",
            },
        )

    def test_prefixes_title_for_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4890",
                "title": "Create",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4890",
                "title": "Cursor researching: Create",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issue_id": "POI-4890",
            "title": "Create",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4890",
                "title": "Cursor researching: Create",
            },
        )

    def test_returns_none_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4890",
            "title": "Create",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4890",
            "title": "Create",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4890",
            "title": "cursor researching: Create",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4890",
                "title": "Create",
            }
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4890",
                "title": "Cursor researching: Create",
            },
        )


if __name__ == "__main__":
    unittest.main()
