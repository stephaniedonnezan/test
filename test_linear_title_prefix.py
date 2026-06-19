import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-3869",
                "title": "Quick win: Turn2X feedback - counter reading bad request",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3869",
                "title": (
                    "Cursor researching: Quick win: Turn2X feedback - counter "
                    "reading bad request"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3869",
                "title": "Quick win: Turn2X feedback - counter reading bad request",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3869",
                "title": "Quick win: Turn2X feedback - counter reading bad request",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3869",
            "title": "Quick win: Turn2X feedback - counter reading bad request",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-3869",
                    "title": "Quick win: Turn2X feedback - counter reading bad request",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3869",
                "title": (
                    "Cursor researching: Quick win: Turn2X feedback - counter "
                    "reading bad request"
                ),
            },
        )

    def test_accepts_changed_fields_new_value_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "issueId": "POI-3869",
            "title": "Quick win: Turn2X feedback - counter reading bad request",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3869",
                "title": (
                    "Cursor researching: Quick win: Turn2X feedback - counter "
                    "reading bad request"
                ),
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "identifier": "POI-3869",
            "title": "  Quick win: Turn2X feedback - counter reading bad request  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3869",
                "title": (
                    "Cursor researching: Quick win: Turn2X feedback - counter "
                    "reading bad request"
                ),
            },
        )

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3869",
            "title": "cursor researching: Quick win",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Quick win",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3869",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_main_prints_update_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3869",
            "title": "Quick win",
        }
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-3869",
                "title": "Cursor researching: Quick win",
            },
        )


if __name__ == "__main__":
    unittest.main()
