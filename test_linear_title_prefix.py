import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_automation_research_status_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                    "status": "To Research",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_ignores_non_research_status(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "In Review",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )
        )

    def test_ignores_non_status_trigger(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )
        )

    def test_ignores_existing_prefix_case_insensitively(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5093",
                    "title": "cursor researching: MB export post QA updates",
                }
            )
        )

    def test_normalizes_camel_case_trigger_and_kebab_status(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "newStatus": "to-research",
                    "issueId": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )["title"],
            "Cursor researching: MB export post QA updates",
        )

    def test_supports_generic_update_with_updated_status_field(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["description", "status"],
                    "newStatus": "To Research",
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )["issueId"],
            "POI-5093",
        )

    def test_ignores_generic_update_without_status_field(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["description"],
                    "newStatus": "To Research",
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )
        )

    def test_extracts_status_from_changes_payload(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "type": "Issue Updated",
                    "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )["title"],
            "Cursor researching: MB export post QA updates",
        )

    def test_extracts_status_from_flat_change_record(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "action": "updated",
                    "changes": {"field": "workflowState", "to": {"name": "To Research"}},
                    "key": "POI-5093",
                    "title": "MB export post QA updates",
                }
            )["issueId"],
            "POI-5093",
        )

    def test_supports_nested_linear_data_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: MB export post QA updates",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"}))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
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
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )


if __name__ == "__main__":
    unittest.main()
