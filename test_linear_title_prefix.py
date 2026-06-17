import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_gets_prefixed_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4997",
                "title": "Local meter supplier uuid says optional but is mandatory",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4997",
                "title": (
                    "Cursor researching: "
                    "Local meter supplier uuid says optional but is mandatory"
                ),
            },
        )

    def test_direct_flat_payload_gets_prefixed_title(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-123",
            "title": "Review supplier UUID label",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review supplier UUID label",
            },
        )

    def test_nested_linear_status_update_payload_gets_prefixed_title(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-234",
                    "title": "Clarify supplier UUID requirement",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-234",
                "title": "Cursor researching: Clarify supplier UUID requirement",
            },
        )

    def test_update_payload_can_read_changed_status_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-345",
                    "title": "Audit field labels",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-345",
                "title": "Cursor researching: Audit field labels",
            },
        )

    def test_case_and_separator_variants_match_to_research(self):
        event = {
            "trigger": "status-changed",
            "new_status": "ToResearch",
            "identifier": "POI-456",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Normalize status names",
            },
        )

    def test_non_status_trigger_is_ignored_even_if_status_matches(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-567",
            "title": "Do not update for comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_update_without_status_field_change_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "identifier": "POI-678",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_other_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-789",
            "title": "Already reviewed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-890",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-901",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-902",
            "title": "CLI payload",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-902",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
