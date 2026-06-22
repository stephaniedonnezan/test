import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_accepts_nested_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5047",
                "title": "Always highlight the field that causes an error state",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_accepts_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-5047",
                    "title": "Always highlight the field that causes an error state",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_accepts_status_name_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"newValue": "to_research"}},
            "data": {
                "issue": {
                    "identifier": "POI-5047",
                    "title": "Always highlight the field that causes an error state",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_accepts_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "cursor researching: Always highlight the field that causes an error state",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "cursor researching: Always highlight the field that causes an error state",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5047",
                }
            )
        )

        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Always highlight the field that causes an error state",
                }
            )
        )

    def test_cli_prints_update_action_for_stdin_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5047",
            "title": "Always highlight the field that causes an error state",
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5047",
                "title": "Cursor researching: Always highlight the field that causes an error state",
            },
        )


if __name__ == "__main__":
    unittest.main()
