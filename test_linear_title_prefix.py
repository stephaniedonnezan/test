import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_status_changed_to_research_returns_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": 'Cursor researching: Redesign of "Add Input"',
            },
        )

    def test_lowercase_to_research_status_returns_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], 'Cursor researching: Redesign of "Add Input"')

    def test_current_dev_status_payload_is_ignored(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
                "status": "DEV",
                "statusType": "started",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_already_prefixed_title_is_ignored_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4838",
                "title": 'cursor researching: Redesign of "Add Input"',
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_normalization_accepts_camel_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], 'Cursor researching: Redesign of "Add Input"')

    def test_nested_linear_issue_update_uses_state_name(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "identifier": "POI-4838",
                    "title": 'Redesign of "Add Input"',
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin_123",
                "title": 'Cursor researching: Redesign of "Add Input"',
            },
        )

    def test_generic_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "lin_123",
                    "title": 'Redesign of "Add Input"',
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changed_fields_dict_can_mark_status_change(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
                "workflowState": {"name": "To Research"},
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-4838")

    def test_missing_title_or_issue_id_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4838",
            }
        }

        self.assertIsNone(build_issue_title_update(event))
        event["triggerContext"].pop("id")
        event["triggerContext"]["title"] = 'Redesign of "Add Input"'
        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4838",
                "title": 'Cursor researching: Redesign of "Add Input"',
            },
        )

    def test_cli_exits_one_for_non_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4838",
                "title": 'Redesign of "Add Input"',
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
