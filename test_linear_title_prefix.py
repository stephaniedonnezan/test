import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_research_status_change(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4773",
                "title": "CO2 stock",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4773",
                "title": "CO2 stock",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_trigger(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4773",
                "title": "CO2 stock",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4773",
                "title": "cursor researching: CO2 stock",
            }
        )

        self.assertIsNone(update)

    def test_normalizes_status_and_trigger_casing(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-4773",
                "title": "CO2 stock",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: CO2 stock")

    def test_accepts_automation_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-1",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4773",
                    "title": "CO2 stock",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4773")
        self.assertEqual(update["title"], "Cursor researching: CO2 stock")

    def test_accepts_nested_linear_issue_update_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-4773",
                        "title": "CO2 stock",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )

    def test_accepts_updated_fields_mapping_with_workflow_state(self):
        update = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": {"workflowState": {"old": "Backlog", "new": "To Research"}},
                "data": {
                    "issue": {
                        "id": "issue-id",
                        "title": "Map feedstock source",
                        "workflowState": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "issue-id")
        self.assertEqual(update["title"], "Cursor researching: Map feedstock source")

    def test_requires_status_field_for_generic_update(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "identifier": "POI-4773",
                        "title": "CO2 stock",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(update)

    def test_returns_none_for_missing_title_or_issue_id(self):
        missing_title = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4773",
            }
        )
        missing_id = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "CO2 stock",
            }
        )

        self.assertIsNone(missing_title)
        self.assertIsNone(missing_id)

    def test_cli_prints_update_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4773",
            "title": "CO2 stock",
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
                "issueId": "POI-4773",
                "title": "Cursor researching: CO2 stock",
            },
        )


if __name__ == "__main__":
    unittest.main()
