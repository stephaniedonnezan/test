import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3943",
                "title": "Feedstock-to-Nabisy-Biomasse-Code lookup table",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3943",
                "title": (
                    "Cursor researching: "
                    "Feedstock-to-Nabisy-Biomasse-Code lookup table"
                ),
            },
        )

    def test_non_target_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-3943",
                "title": "Feedstock-to-Nabisy-Biomasse-Code lookup table",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "  To_Research ",
                "id": "POI-1",
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

    def test_non_status_trigger_is_ignored_even_with_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2",
                "title": "Investigate issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "cursor researching: Investigate issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_updated_fields_is_supported(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested status change",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested status change",
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-5",
                    "title": "Description changed",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_from_changes_prefers_new_value(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {"identifier": "POI-6", "title": "Changed status"},
                "changes": {
                    "status": {
                        "from": {"name": "Backlog"},
                        "to": {"name": "to research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Changed status",
            },
        )

    def test_missing_issue_data_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "No id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "id": "POI-7",
                "title": "CLI sample",
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI sample",
            },
        )


if __name__ == "__main__":
    unittest.main()
