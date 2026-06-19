import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_cursor_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5058",
                "title": "cursor researching: Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants_for_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "TO-RESEARCH",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Move the mb-data-manager into the psqo module",
        )

    def test_uses_trigger_context_inside_full_automation_payload(self):
        event = {
            "automationId": "not-the-issue-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5058")

    def test_accepts_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_ignores_generic_issue_updates_without_status_metadata(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_new_status_over_fallback_status_fields(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "In Progress",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
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
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )


if __name__ == "__main__":
    unittest.main()
