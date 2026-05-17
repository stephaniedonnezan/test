import json
import subprocess
import sys
import unittest

from linear_title_prefix import buildIssueTitleUpdate, build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4609",
                "title": "Update MB export in the audit section",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4609",
                "title": "Cursor researching: Update MB export in the audit section",
            },
        )

    def test_supports_automation_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "To Research",
                    "id": "POI-4609",
                    "title": "Update MB export in the audit section",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4609")
        self.assertEqual(
            update["title"],
            "Cursor researching: Update MB export in the audit section",
        )

    def test_case_and_separator_insensitive_status_matching(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "TO_RESEARCH",
                "issueId": "POI-1",
                "title": "Investigate container weights",
            }
        )

        self.assertEqual(
            update["title"], "Cursor researching: Investigate container weights"
        )

    def test_ignores_other_new_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "Todo",
                    "id": "POI-4609",
                    "title": "Update MB export in the audit section",
                }
            )
        )

    def test_ignores_non_status_change_triggers(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-4609",
                    "title": "Update MB export in the audit section",
                }
            )
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4609",
                    "title": "cursor researching: Update MB export",
                }
            )
        )

    def test_supports_nested_linear_issue_updated_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "id": "linear-issue-id",
                    "identifier": "POI-4609",
                    "title": "Update MB export in the audit section",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "linear-issue-id")
        self.assertEqual(
            update["title"],
            "Cursor researching: Update MB export in the audit section",
        )

    def test_supports_nested_issue_object_under_data(self):
        update = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": ["workflowState"],
                "data": {
                    "issue": {
                        "identifier": "POI-2",
                        "title": "Review audit export",
                        "workflowState": {"name": "To-Research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-2")
        self.assertEqual(update["title"], "Cursor researching: Review audit export")

    def test_status_update_requires_status_related_field_for_generic_update(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["description"],
                    "data": {
                        "id": "POI-3",
                        "title": "Review audit export",
                        "state": {"name": "To Research"},
                    },
                }
            )
        )

    def test_updated_from_status_key_also_counts_as_status_change(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFrom": {"workflowState": "Todo"},
                "data": {
                    "id": "POI-4",
                    "title": "Review audit export",
                    "workflowState": {"name": "toResearch"},
                },
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Review audit export")

    def test_ignores_missing_issue_details(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4609",
                }
            )
        )

    def test_rejects_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_camel_case_wrapper_matches_snake_case_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Review audit export",
        }

        self.assertEqual(buildIssueTitleUpdate(event), build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "Review audit export",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Review audit export",
            },
        )


if __name__ == "__main__":
    unittest.main()
