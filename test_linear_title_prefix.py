import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3628",
                "title": "Update Transport Event to have TransportEventLocationEntity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3628",
                "title": (
                    "Cursor researching: "
                    "Update Transport Event to have TransportEventLocationEntity"
                ),
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To_Research",
            "issueId": "POI-1",
            "title": "Investigate vessel ETA",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Investigate vessel ETA")

    def test_uses_status_when_new_status_is_not_present(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "identifier": "POI-2",
            "title": "Research appointment flow",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research appointment flow",
        )

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Review demurrage fields",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Review demurrage fields",
            },
        )

    def test_supports_changes_map_for_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": "to research"}},
            "data": {
                "issue": {
                    "id": "linear-id",
                    "identifier": "POI-4",
                    "title": "Analyze container release edge cases",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Analyze container release edge cases",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Existing research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing research issue",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-6",
            "title": "Implement transport event locations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "Research comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-8",
            "title": "Only title changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_missing_issue_details(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
        }

        self.assertIsNone(build_issue_title_update(event))


class MainTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "Research CLI path",
        }

        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: Research CLI path",
            },
        )


if __name__ == "__main__":
    unittest.main()
