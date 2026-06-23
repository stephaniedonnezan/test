import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5109",
                "title": "Acceptance suite",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5109",
                "title": "Cursor researching: Acceptance suite",
            },
        )

    def test_accepts_nested_automation_trigger_info(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5110",
                    "title": "Processor graph",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5110",
                "title": "Cursor researching: Processor graph",
            },
        )

    def test_accepts_status_field_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-5111",
                "title": "Status fallback",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Status fallback",
        )

    def test_ignores_other_target_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-5112",
                "title": "Review task",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5113",
                "title": "Comment task",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5114",
                "title": "cursor researching: Already prefixed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_and_separators(self):
        event = {
            "automationTriggerInfo": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to-research",
                    "identifier": "POI-5115",
                    "title": "Normalized task",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalized task",
        )

    def test_accepts_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-5116",
                "title": "Linear task",
                "state": {"name": "To Research"},
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5116",
                "title": "Cursor researching: Linear task",
            },
        )

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-5117",
                "title": "Description edit",
                "state": {"name": "To Research"},
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_target_status_from_change_object(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-5118",
                "title": "Change payload",
                "changes": {"status": {"newValue": "To Research"}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5118",
        )

    def test_returns_none_for_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Missing id",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-5119",
                    }
                }
            )
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-5120 ",
                "title": "  Trimmed task  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5120",
                "title": "Cursor researching: Trimmed task",
            },
        )

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5121",
                "title": "CLI task",
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
                "issueId": "POI-5121",
                "title": "Cursor researching: CLI task",
            },
        )


if __name__ == "__main__":
    unittest.main()
