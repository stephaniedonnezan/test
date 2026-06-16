import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_research_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "id": "POI-4937",
                "title": "cursor researching: Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "identifier": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_falls_back_to_current_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "issueId": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_handles_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4937",
                    "title": "Error: Unit kg is not supported for Electricity",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_handles_status_value_from_changes_mapping(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "changes": {
                    "workflowState": {
                        "oldValue": {"name": "Todo"},
                        "newValue": {"name": "To Research"},
                    }
                },
                "issue": {
                    "id": "POI-4937",
                    "title": "Error: Unit kg is not supported for Electricity",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4937",
                    "title": "Error: Unit kg is not supported for Electricity",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4937",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
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
                "issueId": "POI-4937",
                "title": "Cursor researching: Error: Unit kg is not supported for Electricity",
            },
        )


if __name__ == "__main__":
    unittest.main()
