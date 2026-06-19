import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4520",
                "title": "Do we need a frontend?",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4520",
                "title": "Cursor researching: Do we need a frontend?",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4520",
                "title": "Do we need a frontend?",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4520",
                "title": "Do we need a frontend?",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4520",
                "title": "cursor researching: Do we need a frontend?",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4520",
                "title": "Do we need a frontend?",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Do we need a frontend?",
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4520",
                    "title": "Do we need a frontend?",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4520",
                "title": "Cursor researching: Do we need a frontend?",
            },
        )

    def test_accepts_new_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"newValue": "To Research"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Do we need a frontend?",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Do we need a frontend?",
        )

    def test_changes_new_value_takes_precedence_over_stale_state(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "changes": {"state": {"newValue": "To Research"}},
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Do we need a frontend?",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Do we need a frontend?",
        )

    def test_accepts_list_style_change_records(self):
        event = {
            "action": "update",
            "changes": [{"field": "workflowState", "to": {"name": "To Research"}}],
            "data": {
                "issue": {
                    "identifier": "POI-4520",
                    "title": "Do we need a frontend?",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4520",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4520",
                }
            )
        )

    def test_cli_emits_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4520",
                "title": "Do we need a frontend?",
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
                "issueId": "POI-4520",
                "title": "Cursor researching: Do we need a frontend?",
            },
        )


if __name__ == "__main__":
    unittest.main()
