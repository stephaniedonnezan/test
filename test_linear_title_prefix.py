import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-4934",
                "title": "Container issues panel",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Container issues panel",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "cursor researching: Container issues panel",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4934",
                    "title": "Issues panel must be visible across all tabs",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"oldValue": "Backlog", "newValue": "to_research"}},
            "data": {
                "issue": {
                    "id": "POI-4934",
                    "title": "Container issues panel",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Container issues panel",
            },
        )

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Container issues panel",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_cli_prints_json_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4934",
                "title": "Container issues panel",
            }
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Container issues panel",
            },
        )


if __name__ == "__main__":
    unittest.main()
