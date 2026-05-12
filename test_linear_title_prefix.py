import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_for_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4682",
                "title": "Fix allocation error",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4682",
                "title": "Cursor researching: Fix allocation error",
            },
        )

    def test_supports_automation_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4682",
                    "title": "Investigate energy allocation",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4682")
        self.assertEqual(
            update["title"], "Cursor researching: Investigate energy allocation"
        )

    def test_normalizes_status_case_and_separators(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "TO_RESEARCH",
                "issueId": "POI-1",
                "title": "Research this",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Research this")

    def test_uses_status_fallback_when_new_status_is_absent(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "status": "To Research",
                "identifier": "POI-2",
                "title": "Needs investigation",
            }
        )

        self.assertEqual(update["issueId"], "POI-2")

    def test_supports_nested_linear_issue_update_with_updated_fields(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "issue-id",
                        "title": "Nested issue",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "issue-id")
        self.assertEqual(update["title"], "Cursor researching: Nested issue")

    def test_supports_workflow_state_payloads(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFrom": {"workflowState": {"name": "Todo"}},
                "issue": {
                    "identifier": "POI-3",
                    "title": "Workflow state issue",
                    "workflowState": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            update["title"], "Cursor researching: Workflow state issue"
        )

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4",
                "title": "No prefix",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_events(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5",
                "title": "No prefix",
            }
        )

        self.assertIsNone(update)

    def test_ignores_issue_updates_without_status_field_changes(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "id": "POI-6",
                        "title": "Title changed",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(update)

    def test_skips_already_prefixed_titles_case_insensitively(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": "cursor researching: Already handled",
            }
        )

        self.assertIsNone(update)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research"}
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "CLI event",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
