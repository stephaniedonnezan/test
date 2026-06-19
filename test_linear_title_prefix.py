import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4249",
                "title": "cursor researching: Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "stateChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_handles_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_handles_new_status_from_changes_mapping(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "id": "8f4f",
                    "title": "Trader: Add dispatch date sanity check",
                }
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "8f4f",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_handles_new_status_from_changes_list(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "key": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                }
            },
            "changes": [
                {
                    "field": "status",
                    "oldValue": "Backlog",
                    "newValue": {"name": "To Research"},
                }
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4249",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_as_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )


if __name__ == "__main__":
    unittest.main()
