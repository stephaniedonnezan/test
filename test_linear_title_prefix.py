import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_to_research_event(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4480",
                "title": "GET /energy-allocation failed with status code 400",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4480",
                "title": "Cursor researching: GET /energy-allocation failed with status code 400",
            },
        )

    def test_accepts_flat_status_change_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4480",
            "title": "Investigate energy allocation request",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4480",
                "title": "Cursor researching: Investigate energy allocation request",
            },
        )

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["stateId"],
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-4480",
                    "title": "Investigate energy allocation request",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate energy allocation request",
            },
        )

    def test_accepts_changed_fields_mapping_with_workflow_state(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "changedFields": {"workflowState": {"old": "Backlog", "new": "To Research"}},
                "issue": {
                    "identifier": "POI-4480",
                    "title": "Investigate energy allocation request",
                    "workflowState": {"name": "to-research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4480",
                "title": "Cursor researching: Investigate energy allocation request",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4480",
            "title": "Investigate energy allocation request",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "issue_created",
            "newStatus": "To Research",
            "id": "POI-4480",
            "title": "Investigate energy allocation request",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_when_status_field_did_not_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "id": "issue-uuid",
                    "title": "Investigate energy allocation request",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4480",
            "title": "cursor researching: Investigate energy allocation request",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4480",
                }
            )
        )

    def test_main_prints_update_from_stdin_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4480",
            "title": "Investigate energy allocation request",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4480",
                "title": "Cursor researching: Investigate energy allocation request",
            },
        )


if __name__ == "__main__":
    unittest.main()
