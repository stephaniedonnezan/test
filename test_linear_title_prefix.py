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
                "newStatus": "to research",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: [FE]Refine the dialog(s) in the Meters Page",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-100",
                "title": "Investigate meter dialog spacing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate meter dialog spacing",
        )

    def test_prefixes_nested_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "data": {
                "type": "Issue",
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-200",
                    "title": "Research meter page popups",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-200",
                "title": "Cursor researching: Research meter page popups",
            },
        )

    def test_uses_changed_status_value_before_current_issue_state(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["workflowState"],
                "issue": {
                    "identifier": "POI-300",
                    "title": "Current state may lag",
                    "workflowState": {"name": "Backlog"},
                },
                "changes": {
                    "workflowState": {
                        "from": {"name": "Backlog"},
                        "to": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Current state may lag",
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA UX/UI",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-400",
                    "title": "Rename only",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_explicit_new_status_on_unrelated_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-500",
                "title": "Comment should not update title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-600",
                "title": "cursor researching: Existing research title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Missing issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_compact_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-700",
                "title": "CLI payload",
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
            result.stdout.strip(),
            '{"action":"update_issue_title","issueId":"POI-700","title":"Cursor researching: CLI payload"}',
        )


if __name__ == "__main__":
    unittest.main()
