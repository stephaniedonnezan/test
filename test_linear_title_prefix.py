import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4859",
                "title": "Unify PHP implementation and get rid of ts local stuff",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: Unify PHP implementation and get rid of ts local stuff",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4859",
                "title": "Unify PHP implementation and get rid of ts local stuff",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4859",
                "title": "Unify PHP implementation and get rid of ts local stuff",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4859",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4859",
                "title": "Investigate a webhook",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: Investigate a webhook",
            },
        )

    def test_handles_nested_linear_issue_update_state_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4859",
                "title": "Nested Linear issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_handles_nested_issue_object(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4859",
                    "title": "Nested issue object",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: Nested issue object",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4859",
                "title": "Changed status payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: Changed status payload",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4859",
                "title": "Renamed issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4859",
                    }
                }
            )
        )

    def test_safely_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))


class MainTest(unittest.TestCase):
    def test_cli_prints_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4859",
                "title": "CLI issue",
            }
        }

        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(output):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4859",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
