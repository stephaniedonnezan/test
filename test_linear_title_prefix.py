import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5041",
                "title": "Supply contracts are not only inputting producer",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5041",
                "title": "Cursor researching: Supply contracts are not only inputting producer",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5041",
                "title": "Supply contracts are not only inputting producer",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5041",
                "title": "Supply contracts are not only inputting producer",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-5041",
                "title": "Supply contracts are not only inputting producer",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Supply contracts are not only inputting producer",
        )

    def test_accepts_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5041",
                    "title": "Supply contracts are not only inputting producer",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5041",
                "title": "Cursor researching: Supply contracts are not only inputting producer",
            },
        )

    def test_accepts_change_map_new_status_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5041",
                    "title": "Supply contracts are not only inputting producer",
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
            build_issue_title_update(event)["issueId"],
            "POI-5041",
        )

    def test_uses_flat_status_for_status_changed_events(self):
        event = {
            "trigger": "state_changed",
            "status": "toResearch",
            "issueId": "POI-5041",
            "title": "Supply contracts are not only inputting producer",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Supply contracts are not only inputting producer",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5041",
                "title": "cursor researching: Supply contracts are not only inputting producer",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Supply contracts are not only inputting producer",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5041",
                "title": "Supply contracts are not only inputting producer",
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
                "issueId": "POI-5041",
                "title": "Cursor researching: Supply contracts are not only inputting producer",
            },
        )


if __name__ == "__main__":
    unittest.main()
