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
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4965",
                "title": "performance: fetch meter readings once",
                "status": "In Review",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4965",
            "title": "Grid mix performance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Grid mix performance",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4965",
            "title": "Grid mix performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-4965",
            "title": "Grid mix performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "state": {"name": "To Research"},
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Grid mix performance",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Grid mix performance",
            },
        )

    def test_nested_linear_changes_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "identifier": "POI-4965",
                    "title": "Grid mix performance",
                }
            },
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Grid mix performance",
            },
        )

    def test_skips_existing_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4965",
            "title": "cursor researching: Grid mix performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Grid mix performance",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4965",
                }
            )
        )

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4965",
                "title": "Grid mix performance",
            }
        }

        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Grid mix performance",
            },
        )


if __name__ == "__main__":
    unittest.main()
