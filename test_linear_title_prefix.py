import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_ignores_flat_cursor_trigger_context_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_separator_and_camel_case_status_variants(self):
        statuses = ("To Research", "to_research", "to-research", "toResearch")

        for status in statuses:
            with self.subTest(status=status):
                self.assertEqual(
                    build_issue_title_update(
                        {
                            "triggerContext": {
                                "trigger": "statusChanged",
                                "newStatus": status,
                                "issueId": "POI-1",
                                "title": "Needs investigation",
                            }
                        }
                    )["title"],
                    "Cursor researching: Needs investigation",
                )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2",
                "title": "cursor researching: Existing work",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_unrelated_triggers_even_with_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "No status transition",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_supports_new_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "changes": {
                    "status": {
                        "oldValue": "Todo",
                        "newValue": "To Research",
                    }
                },
                "issue": {
                    "identifier": "POI-5",
                    "title": "Changed through payload",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed through payload",
        )

    def test_does_not_use_updated_from_previous_status_as_target(self):
        event = {
            "action": "update",
            "data": {
                "updatedFrom": {"status": "To Research"},
                "issue": {
                    "identifier": "POI-6",
                    "title": "Moved away from research",
                    "state": {"name": "DEV"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identity_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-7",
                    }
                }
            )
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "Alias handler",
            },
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


class CommandLineTest(unittest.TestCase):
    def test_cli_prints_update_action_for_json_stdin(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "CLI event",
            },
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
                "issueId": "POI-9",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
