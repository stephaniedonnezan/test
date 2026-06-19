import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4278",
                "title": "follow up downstream emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4278",
                "title": "Cursor researching: follow up downstream emissions",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Audit payment imports",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Audit payment imports",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-2",
            "title": "Build export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Build export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Build export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Improve ingestion reliability",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Improve ingestion reliability",
            },
        )

    def test_handles_status_change_from_changes_object(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"old": "Triage", "new": "to_research"}},
            "identifier": "POI-6",
            "title": "Reconcile balances",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Reconcile balances",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_action_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "Review trader workflow",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(payload))):
            with redirect_stdout(stdout):
                self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Review trader workflow",
            },
        )


if __name__ == "__main__":
    unittest.main()
