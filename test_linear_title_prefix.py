import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5021",
            "title": "Add hydrogen input does not change anything in mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Add hydrogen input does not change anything in mass balance",
            },
        )

    def test_cursor_trigger_context_payload_adds_prefix(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5021",
                "title": "Investigate hydrogen input persistence",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Investigate hydrogen input persistence",
            },
        )

    def test_nested_linear_update_uses_state_name_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5021",
                "title": "Research title updates",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Research title updates",
            },
        )

    def test_changes_payload_extracts_new_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"workflowState": {"newValue": {"name": "To Research"}}},
            "data": {"identifier": "POI-5021", "title": "Workflow state change"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Workflow state change",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issue_id": "POI-5021",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5021",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "status": "To Research",
            "id": "POI-5021",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-5021",
                "title": "Description changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_cursor_researching_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5021",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "title": "No ID"}))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research", "id": "POI-5021"}))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-5021 ",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5021",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_cli_prints_title_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5021",
            "title": "CLI payload",
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
                "issueId": "POI-5021",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
