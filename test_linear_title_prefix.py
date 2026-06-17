import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5030",
                "title": "Ability to fetch data from QA and Prod safely",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: Ability to fetch data from QA and Prod safely",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-5030",
            "title": "QA and prod reads",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: QA and prod reads",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5030",
            "title": "Ability to fetch data from QA and Prod safely",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5030",
            "title": "Ability to fetch data from QA and Prod safely",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5030",
            "title": "cursor researching: Ability to fetch data from QA and Prod safely",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_linear_update_with_state_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5030",
                "title": "Ability to fetch data from QA and Prod safely",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: Ability to fetch data from QA and Prod safely",
            },
        )

    def test_accepts_nested_issue_payload(self):
        event = {
            "eventType": "Issue Updated",
            "changedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5030",
                    "title": "Ability to fetch data from QA and Prod safely",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: Ability to fetch data from QA and Prod safely",
            },
        )

    def test_accepts_object_shaped_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": {"status": {"to": "To Research"}},
            "issue": {
                "identifier": "POI-5030",
                "title": "Ability to fetch data from QA and Prod safely",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: Ability to fetch data from QA and Prod safely",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5030",
            "title": "Ability to fetch data from QA and Prod safely",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5030",
                "title": "Cursor researching: Ability to fetch data from QA and Prod safely",
            },
        )


if __name__ == "__main__":
    unittest.main()
