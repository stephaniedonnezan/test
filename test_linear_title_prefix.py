import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3477",
                "title": "Change name from Filling to Loading event",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3477",
                "title": "Cursor researching: Change name from Filling to Loading event",
            },
        )

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "id": "POI-1",
            "title": "Investigate exporter mismatch",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate exporter mismatch",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3477",
            "title": "Change name from Filling to Loading event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-3477",
            "title": "Change name from Filling to Loading event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3477",
            "title": "cursor researching: Change name from Filling to Loading event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-3477",
                    "title": "Change name from Filling to Loading event",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3477",
                "title": "Cursor researching: Change name from Filling to Loading event",
            },
        )

    def test_handles_issue_updated_with_status_change_details(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "changes": [
                    {
                        "field": "workflowState",
                        "newValue": {"name": "To Research"},
                    }
                ],
                "issue": {
                    "id": "issue-id",
                    "title": "Research state from change payload",
                    "workflowState": {"name": "Backlog"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research state from change payload",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))

    def test_cli_prints_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3477",
            "title": "Change name from Filling to Loading event",
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-3477",
                "title": "Cursor researching: Change name from Filling to Loading event",
            },
        )

    def test_cli_stays_quiet_when_no_action_is_needed(self):
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO("{}")), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
