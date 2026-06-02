import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate export headers",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate export headers",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-123",
            "title": "Investigate export headers",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Investigate export headers",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "cursor researching: Investigate export headers",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-456",
                "title": "Research mass-balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research mass-balance export",
            },
        )

    def test_handles_updated_from_status_payloads(self):
        event = {
            "action": "updated",
            "updatedFrom": {"status": "Backlog"},
            "data": {
                "id": "issue-uuid",
                "title": "Clarify methane calculation",
                "status": "to research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Clarify methane calculation",
            },
        )

    def test_handles_nested_trigger_context_data_issue(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "data": {
                    "issue": {
                        "identifier": "POI-789",
                        "title": "Review stored MB defaults",
                        "workflowState": {"name": "To Research"},
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review stored MB defaults",
            },
        )

    def test_normalizes_status_and_event_variants(self):
        event = {
            "eventType": "workflow-state-changed",
            "newStatus": "to_research",
            "id": "POI-321",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Normalize status names",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-123"}
            )
        )

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))  # type: ignore[arg-type]

    def test_cli_prints_update_for_valid_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate automation",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate automation",
            },
        )


if __name__ == "__main__":
    unittest.main()
