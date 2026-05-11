import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_event(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2809",
                "title": "[625]Create new site entity",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2809",
                "title": "Cursor researching: [625]Create new site entity",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2809",
                "title": "[625]Create new site entity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-2809",
                "title": "[625]Create new site entity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-2809",
                "title": "cursor researching: [625]Create new site entity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "to_research",
                "id": "POI-2809",
                "title": "  [625]Create new site entity  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2809",
                "title": "Cursor researching: [625]Create new site entity",
            },
        )

    def test_accepts_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2809",
                    "title": "[625]Create new site entity",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2809",
                "title": "Cursor researching: [625]Create new site entity",
            },
        )

    def test_requires_updated_status_field_for_generic_issue_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-2809",
                    "title": "[625]Create new site entity",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_updated_fields_map_from_linear_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"oldValue": "Backlog", "newValue": "To Research"}},
            "data": {
                "id": "issue-uuid",
                "title": "[625]Create new site entity",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: [625]Create new site entity",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2809",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_json_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2809",
                "title": "[625]Create new site entity",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-2809",
                "title": "Cursor researching: [625]Create new site entity",
            },
        )


if __name__ == "__main__":
    unittest.main()
