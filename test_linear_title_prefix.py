import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "GET /automate/sites failed",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_uses_trigger_context_payload_shape(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4644",
                "title": "Sentry error",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Sentry error",
            },
        )

    def test_accepts_status_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-1",
            "title": "Investigate this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate this",
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Triage",
            "id": "POI-4644",
            "title": "GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "cursor researching: GET /automate/sites failed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-4644",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_supports_nested_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Nested issue object",
                    "workflowState": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Nested issue object",
            },
        )

    def test_prefers_explicit_new_status_over_nested_stale_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4644",
                "title": "Explicit status wins",
                "state": {"name": "Triage"},
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Explicit status wins",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4644 ",
            "title": "  Needs investigation  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Needs investigation",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "CLI issue",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
