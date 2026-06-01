import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4401",
                "title": "File processing services",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4401",
                "title": "Cursor researching: File processing services",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4401",
            "title": "File processing services",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4401",
            "title": "File processing services",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4401",
            "title": "cursor researching: File processing services",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_hyphenated_status_and_trimmed_title(self):
        event = {
            "trigger": "status-changed",
            "status": "to-research",
            "id": " POI-4401 ",
            "title": "  File processing services  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4401",
                "title": "Cursor researching: File processing services",
            },
        )

    def test_handles_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4401",
                "title": "File processing services",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: File processing services",
            },
        )

    def test_handles_workflow_state_name(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": {"workflowState": {"old": "Backlog"}},
            "data": {
                "identifier": "POI-4401",
                "title": "File processing services",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4401",
                "title": "Cursor researching: File processing services",
            },
        )

    def test_ignores_issue_update_when_updated_fields_do_not_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "File processing services",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_required_fields_are_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research"}
            )
        )

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))  # type: ignore[arg-type]

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4401",
            "title": "File processing services",
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
                "issueId": "POI-4401",
                "title": "Cursor researching: File processing services",
            },
        )


if __name__ == "__main__":
    unittest.main()
