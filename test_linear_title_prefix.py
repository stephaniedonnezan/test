import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_trigger_context_research_status(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3958",
                    "title": "Ensure we can re-open a delivery",
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3958",
                "title": "Cursor researching: Ensure we can re-open a delivery",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_events(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertIsNone(result)

    def test_ignores_titles_that_are_already_prefixed(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-3958",
                "title": "cursor researching: Ensure we can re-open a delivery",
            }
        )

        self.assertIsNone(result)

    def test_matches_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            {
                "action": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )

    def test_matches_camel_case_status_variant(self):
        result = build_issue_title_update(
            {
                "action": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(result["issueId"], "POI-3958")

    def test_uses_nested_linear_data_issue_payload(self):
        result = build_issue_title_update(
            {
                "data": {
                    "action": "statusChanged",
                    "newStatus": "To Research",
                    "issue": {
                        "id": "POI-3958",
                        "title": "Ensure we can re-open a delivery",
                    },
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3958",
                "title": "Cursor researching: Ensure we can re-open a delivery",
            },
        )

    def test_uses_state_name_as_status_fallback(self):
        result = build_issue_title_update(
            {
                "type": "stateChanged",
                "state": {"name": "To Research"},
                "identifier": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(result["issueId"], "POI-3958")

    def test_uses_workflow_state_name_as_status_fallback(self):
        result = build_issue_title_update(
            {
                "type": "workflowStateChanged",
                "workflowState": {"name": "To Research"},
                "identifier": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(result["issueId"], "POI-3958")

    def test_webhook_type_issue_does_not_mask_action_status_change(self):
        result = build_issue_title_update(
            {
                "webhookType": "issue",
                "action": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )

    def test_issue_updated_with_status_field_is_treated_as_status_change(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["status"],
                "status": "To Research",
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )

    def test_issue_updated_with_workflow_state_field_is_treated_as_status_change(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["workflowState"],
                "workflowState": {"name": "To Research"},
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )

    def test_issue_updated_without_status_field_is_ignored(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["title"],
                "status": "To Research",
                "id": "POI-3958",
                "title": "Ensure we can re-open a delivery",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Ensure we can re-open a delivery",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3958",
                }
            )
        )

    def test_trims_issue_id_and_title(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-3958 ",
                "title": " Ensure we can re-open a delivery ",
            }
        )

        self.assertEqual(result["issueId"], "POI-3958")
        self.assertEqual(
            result["title"],
            "Cursor researching: Ensure we can re-open a delivery",
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3958",
                    "title": "Ensure we can re-open a delivery",
                }
            ),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(process.returncode, 0)
        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3958",
                "title": "Cursor researching: Ensure we can re-open a delivery",
            },
        )


if __name__ == "__main__":
    unittest.main()
