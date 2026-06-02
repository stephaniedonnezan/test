import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4184",
                "title": "API-based support for returning unused PPAs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4184",
                "title": "Cursor researching: API-based support for returning unused PPAs",
            },
        )

    def test_uses_status_fallback_for_automation_payloads(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "toResearch",
                "issueId": "issue-id",
                "title": "Research matching behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research matching behavior",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4184",
                "title": "API-based support for returning unused PPAs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4184",
                "title": "API-based support for returning unused PPAs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4184",
                "title": "cursor researching: API-based support for returning unused PPAs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "new_status": "to_research",
                "identifier": "POI-4184",
                "title": "  API-based support for returning unused PPAs  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4184",
                "title": "Cursor researching: API-based support for returning unused PPAs",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-issue-id",
                "title": "Investigate PPA allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Investigate PPA allocation",
            },
        )

    def test_ignores_issue_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "linear-issue-id",
                "title": "Investigate PPA allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4184",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4184",
                "title": "API-based support for returning unused PPAs",
            }
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4184",
                "title": "Cursor researching: API-based support for returning unused PPAs",
            },
        )


if __name__ == "__main__":
    unittest.main()
