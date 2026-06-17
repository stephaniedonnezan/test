import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload_gets_prefixed(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Meter table should display sites",
                "id": "POI-3860",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "title": "Investigate CSV import",
                "id": "POI-1234",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate CSV import",
            },
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Meter table should display sites",
                "id": "POI-3860",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Meter table should display sites",
                "id": "POI-3860",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_already_prefixed_title_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "cursor researching: Meter table should display sites",
                "id": "POI-3860",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_updated_fields_uses_issue_identifier(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "7f4f9d5f-2c43-4a73-bcc1-80b89299ac6b",
                    "identifier": "POI-3860",
                    "title": "Meter table should display sites",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )

    def test_nested_linear_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-3860",
                    "title": "Meter table should display sites",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_change_record_new_value_wins_over_fallback_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "status": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-3860",
                "title": "Meter table should display sites",
                "status": "Backlog",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )

    def test_missing_title_or_issue_id_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-3860",
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
                        "title": "Meter table should display sites",
                    }
                }
            )
        )

    def test_cli_prints_json_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Meter table should display sites",
                "id": "POI-3860",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3860",
                "title": "Cursor researching: Meter table should display sites",
            },
        )


if __name__ == "__main__":
    unittest.main()
