import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_prefixes_title(self):
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
                "title": (
                    "Cursor researching: "
                    "User role not persisiting upon invitation"
                ),
            },
        )

    def test_case_and_separator_insensitive_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": "POI-1",
                "title": "Investigate issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
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
                "id": "POI-2",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "cursor researching: Already prefixed",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "cursor researching: Already prefixed",
            },
        )

    def test_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_generic_update_uses_changed_status_target(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "identifier": "POI-5",
                "title": "Changed status payload",
                "status": {"name": "Todo"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Changed status payload",
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "issue": {
                "identifier": "POI-6",
                "title": "Description only",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_title_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-8",
                "title": "CLI payload",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
