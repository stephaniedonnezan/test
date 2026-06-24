import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_cursor_trigger_context_adds_research_prefix(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4174",
                    "title": "Issues button is now at the wrong place again.",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4174",
                "title": "Cursor researching: Issues button is now at the wrong place again.",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-123",
                "title": "Research this issue",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4174",
                "title": "Already complete",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4174",
                "title": "Commented issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4174",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_linear_issue_update_uses_changes_new_status_before_current_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "changes": {"state": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-555",
                    "title": "Nested Linear issue",
                    "state": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-555",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_nested_issue_identifier_wins_over_webhook_delivery_id(self):
        event = {
            "id": "webhook-delivery-id",
            "action": "update",
            "updatedFields": ["state"],
            "changes": {"state": {"to": "to research"}},
            "data": {
                "issue": {
                    "identifier": "POI-999",
                    "title": "Use issue identifier",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-999",
                "title": "Cursor researching: Use issue identifier",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "identifier": "POI-777",
            "title": "Description-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_or_issue_id_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "No issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-888",
                "title": "CLI issue",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-888",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
