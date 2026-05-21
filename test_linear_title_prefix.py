import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4661",
                "title": "Cursor researching: Exclude trading sites from the energy allocation",
            },
        )

    def test_alias_uses_same_handler(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-1",
                "title": "Research task",
            }
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4661",
                "title": "Exclude trading sites from the energy allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4661",
                "title": "cursor researching: Exclude trading sites",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_case(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "TO_RESEARCH",
                "issueId": "POI-4661",
                "title": "Exclude trading sites",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4661",
                "title": "Cursor researching: Exclude trading sites",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-4661",
                "title": "Exclude trading sites",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Exclude trading sites",
            },
        )

    def test_supports_nested_issue_inside_data(self):
        event = {
            "webhookType": "Issue Updated",
            "updatedFields": {"workflowState": {"name": "Ready"}},
            "data": {
                "issue": {
                    "identifier": "POI-4661",
                    "title": "Exclude trading sites",
                    "workflowState": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4661",
                "title": "Cursor researching: Exclude trading sites",
            },
        )

    def test_ignores_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "linear-issue-id",
                "title": "Exclude trading sites",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Exclude trading sites",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4661",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4661",
                "title": "Exclude trading sites",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4661",
                "title": "Cursor researching: Exclude trading sites",
            },
        )


if __name__ == "__main__":
    unittest.main()
