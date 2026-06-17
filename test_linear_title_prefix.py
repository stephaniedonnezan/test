import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5024",
                "title": "Avoiding MB reopening",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5024",
                "title": "Cursor researching: Avoiding MB reopening",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5024",
                "title": "Avoiding MB reopening",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5024",
                "title": "Avoiding MB reopening",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5024",
                "title": "cursor researching: Avoiding MB reopening",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "4e62d6ed-1bcb-43b2-a403-8617f95f33e4",
                    "identifier": "POI-5024",
                    "title": "Avoiding MB reopening",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5024",
                "title": "Cursor researching: Avoiding MB reopening",
            },
        )

    def test_accepts_changed_status_map(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To-Research"}}},
            "issue": {
                "identifier": "POI-5024",
                "title": "Avoiding MB reopening",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5024",
                "title": "Cursor researching: Avoiding MB reopening",
            },
        )

    def test_ignores_update_without_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-5024",
                    "title": "Avoiding MB reopening",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "toResearch",
                "issueId": " POI-5024 ",
                "title": " Avoiding MB reopening ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5024",
                "title": "Cursor researching: Avoiding MB reopening",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5024",
                "title": "Avoiding MB reopening",
            }
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
                "issueId": "POI-5024",
                "title": "Cursor researching: Avoiding MB reopening",
            },
        )


if __name__ == "__main__":
    unittest.main()
