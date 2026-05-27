import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4743",
                "title": "Certificate change in the middle of the month",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4743",
                "title": "Cursor researching: Certificate change in the middle of the month",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-1",
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-4743",
                    "title": "  Research me  ",
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4743",
                "title": "Cursor researching: Research me",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "linear-issue-id",
                        "identifier": "POI-4743",
                        "title": "Nested issue",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_uses_explicit_new_status_before_nested_current_status(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                },
                "data": {
                    "issue": {
                        "id": "POI-4743",
                        "title": "Stale nested status",
                        "state": {"name": "Todo"},
                    }
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Stale nested status")

    def test_ignores_non_research_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4743",
                "title": "Certificate change in the middle of the month",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_trigger(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4743",
                "title": "Certificate change in the middle of the month",
            }
        )

        self.assertIsNone(result)

    def test_ignores_issue_update_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "id": "POI-4743",
                        "title": "Title-only update",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4743",
                "title": "cursor researching: Already marked",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4743"}
            )
        )

    def test_main_prints_action_as_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4743",
            "title": "CLI issue",
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4743",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
