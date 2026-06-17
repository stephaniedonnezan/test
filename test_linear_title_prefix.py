import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_current_non_research_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA UX/UI",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4962",
                "title": "cursor researching: User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_nested_linear_issue_update_uses_issue_identifier(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "webhook-event-id",
                "issue": {
                    "id": "linear-opaque-issue-id",
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                },
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_nested_linear_changes_object_can_supply_new_status(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                }
            },
            "changes": {"state": {"name": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_nested_linear_changes_list_can_supply_new_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                }
            },
            "changes": [{"field": "workflowState", "to": "toResearch"}],
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4962",
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": " to research ",
            "issueId": " POI-4962 ",
            "title": " User role not persisiting upon invitation ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "A"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI"}
            )
        )

    def test_cli_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )


if __name__ == "__main__":
    unittest.main()
