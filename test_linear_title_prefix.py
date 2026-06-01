import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
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

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
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

    def test_handles_updated_fields_mapping(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": {"status": "old-status-id"},
            "identifier": "POI-456",
            "title": "Research state mapping",
            "workflowState": {"name": "To Research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Research state mapping",
            },
        )

    def test_handles_updated_from_mapping_when_fields_missing(self):
        event = {
            "action": "update",
            "updatedFrom": {"workflowState": {"name": "Backlog"}},
            "identifier": "POI-789",
            "title": "Research updatedFrom fallback",
            "workflowState": {"name": "To Research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Research updatedFrom fallback",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-123",
            "title": "Normalize the status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Normalize the status",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Missing issue ID",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_rejects_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "CLI payload",
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
                "title": "Cursor researching: CLI payload",
            },
        )

    def test_cli_stays_silent_for_non_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-123",
            "title": "CLI payload",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
