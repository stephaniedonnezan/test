import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
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

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "issueId": "POI-4962",
            "title": "Cursor researching: User role not persisiting upon invitation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "trigger": "status-changed",
            "new_status": "TO_RESEARCH",
            "issue_id": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_supports_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4962",
                "title": "User role not persisiting upon invitation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_supports_nested_issue_object(self):
        event = {
            "webhookType": "issue_updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4962",
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4962",
                "title": "User role not persisiting upon invitation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_change_metadata(self):
        event = {
            "action": "updated",
            "changes": [
                {"field": "status", "from": "Backlog", "to": "To Research"}
            ],
            "identifier": "POI-4962",
            "title": "User role not persisiting upon invitation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_requires_issue_identifier(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "User role not persisiting upon invitation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "identifier": "POI-4962",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "identifier": "POI-4962",
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
