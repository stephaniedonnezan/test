import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4608",
                "title": "LHV of H2 is hardcoded to 33.333",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "issue_created",
            "newStatus": "To Research",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4608",
            "title": "cursor researching: LHV of H2 is hardcoded to 33.333",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "issue-uuid",
                    "title": "LHV of H2 is hardcoded to 33.333",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_ignores_linear_update_when_status_field_did_not_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "id": "issue-uuid",
                    "title": "LHV of H2 is hardcoded to 33.333",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changed_fields_mapping_with_workflow_state(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "changedFields": {"workflowState": {"old": "Backlog", "new": "To Research"}},
                "issue": {
                    "identifier": "POI-4608",
                    "title": "LHV of H2 is hardcoded to 33.333",
                    "workflowState": {"name": "to-research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_accepts_status_objects_and_state_id_changed_fields(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["stateId"],
                "id": "issue-uuid",
                "title": "LHV of H2 is hardcoded to 33.333",
                "newStatus": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_accepts_direct_state_string_as_new_status(self):
        event = {
            "trigger": "status_changed",
            "state": "toResearch",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4608 ",
            "title": " LHV of H2 is hardcoded to 33.333 ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4608",
                }
            )
        )

    def test_main_prints_update_from_stdin_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4608",
            "title": "LHV of H2 is hardcoded to 33.333",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4608",
                "title": "Cursor researching: LHV of H2 is hardcoded to 33.333",
            },
        )


if __name__ == "__main__":
    unittest.main()
