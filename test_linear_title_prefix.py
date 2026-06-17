import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
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
                "newStatus": "Backlog",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
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
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "id": "POI-4962",
                "title": "cursor researching: User role not persisiting upon invitation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "cursor researching: User role not persisiting upon invitation",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_accepts_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                }
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

    def test_uses_changed_status_metadata_when_present(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User role not persisiting upon invitation",
        )

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4962",
                    "title": "User role not persisiting upon invitation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"}))
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4962"}
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4962",
                "title": "User role not persisiting upon invitation",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4962",
                "title": "Cursor researching: User role not persisiting upon invitation",
            },
        )


if __name__ == "__main__":
    unittest.main()
