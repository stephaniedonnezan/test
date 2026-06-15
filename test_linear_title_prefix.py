import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4935",
                "title": "Issues indicator is mispositioned in container logic view",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4935",
                "title": (
                    "Cursor researching: Issues indicator is mispositioned in "
                    "container logic view"
                ),
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "id": "POI-1",
                "title": "Normalize research status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize research status",
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-2",
                "title": "Wrong status",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "Wrong trigger",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_falls_back_to_current_status_when_new_status_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-5",
                "title": "Current status fallback",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Current status fallback",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-6",
                "id": "linear-uuid",
                "title": "Nested issue payload",
                "state": {"name": "To Research"},
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_uses_status_change_value_from_changes_mapping(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-7",
                "title": "Changed status mapping",
                "changes": {"state": {"from": "Backlog", "to": "To Research"}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status mapping",
        )

    def test_uses_status_change_value_from_changes_sequence(self):
        event = {
            "action": "issueUpdated",
            "data": {
                "identifier": "POI-8",
                "title": "Changed status sequence",
                "changes": [
                    {"field": "state", "oldValue": "Backlog", "newValue": {"name": "To Research"}}
                ],
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status sequence",
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-9",
                "title": "Generic update",
                "state": {"name": "To Research"},
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "  POI-10  ",
                "title": "  Trimmed title  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_cli_prints_json_action(self):
        payload = json.dumps(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-11",
                    "title": "CLI payload",
                }
            }
        )

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(payload)), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-11",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
