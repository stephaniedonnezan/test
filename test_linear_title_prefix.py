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
                "newStatus": "To Research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )

    def test_prefixes_cloud_automation_trigger_info_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5013",
                    "title": "Loading message goes behind Mass Balance items",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-5013")
        self.assertEqual(
            update["title"],
            "Cursor researching: Loading message goes behind Mass Balance items",
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_when_status_is_research(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "To Research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5013",
                "title": "cursor researching: Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status_value(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Loading message goes behind Mass Balance items",
        )

    def test_accepts_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )

    def test_accepts_changed_status_value_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "type": "Issue",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-5013",
                    "title": "Loading message goes behind Mass Balance items",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Loading message goes behind Mass Balance items",
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payload_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
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
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )


if __name__ == "__main__":
    unittest.main()
