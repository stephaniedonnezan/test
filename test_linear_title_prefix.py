import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_trigger_context(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Auditor who invited by user to an audit is unbranded",
            "id": "POI-4978",
            "status": "To Research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4978",
                "title": "Cursor researching: Auditor who invited by user to an audit is unbranded",
            },
        )

    def test_accepts_full_automation_payload_with_trigger_context(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Invite email lacks Atmen branding",
                "id": "POI-4978",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4978",
                "title": "Cursor researching: Invite email lacks Atmen branding",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4978",
                    "title": "Invite email lacks Atmen branding",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4978",
                "title": "Cursor researching: Invite email lacks Atmen branding",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "issueId": "POI-4978",
            "title": "Invite email lacks Atmen branding",
            "changes": {
                "workflowState": {
                    "from": {"name": "Todo"},
                    "to": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4978",
                "title": "Cursor researching: Invite email lacks Atmen branding",
            },
        )

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "key": "POI-4978",
            "title": "Invite email lacks Atmen branding",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_unrelated_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4978",
            "title": "Invite email lacks Atmen branding",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4978",
            "title": "Invite email lacks Atmen branding",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4978",
            "title": "Invite email lacks Atmen branding",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4978",
            "title": "cursor researching: Invite email lacks Atmen branding",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4978",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_main_prints_action_json_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4978",
            "title": "Invite email lacks Atmen branding",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4978",
                "title": "Cursor researching: Invite email lacks Atmen branding",
            },
        )


if __name__ == "__main__":
    unittest.main()
