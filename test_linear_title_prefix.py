import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5051",
                "title": "Create error if compliant co2 input is not set as 1",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5051",
                "title": "Cursor researching: Create error if compliant co2 input is not set as 1",
            },
        )

    def test_accepts_direct_flat_payload_with_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "  Review methane import  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review methane import",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5051",
            "title": "Create error if compliant co2 input is not set as 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5051",
            "title": "Create error if compliant co2 input is not set as 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5051",
            "title": "cursor researching: Create error if compliant co2 input is not set as 1",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-222",
                "title": "Research feedstock certificate",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-222",
                "title": "Cursor researching: Research feedstock certificate",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-333",
                "title": "Update description",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_change_map(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"old": "Backlog", "new": "To Research"}},
            "issue": {"identifier": "POI-444", "title": "Compare plant options"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-444",
                "title": "Cursor researching: Compare plant options",
            },
        )

    def test_accepts_updated_from_state_id_with_current_workflow_state(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-555",
                "title": "Investigate balance inputs",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-555",
                "title": "Cursor researching: Investigate balance inputs",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-123"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-666",
            "title": "Check synthesis assumptions",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-666",
                "title": "Cursor researching: Check synthesis assumptions",
            },
        )


if __name__ == "__main__":
    unittest.main()
