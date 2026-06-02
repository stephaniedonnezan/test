import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4705",
            "title": "WRT orchestration in delivery transport emissions module",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4705",
                "title": (
                    "Cursor researching: WRT orchestration in delivery transport "
                    "emissions module"
                ),
            },
        )

    def test_supports_cursor_automation_trigger_context_shape(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "status": "to_research",
                "id": "POI-1234",
                "title": "Investigate ingestion delay",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate ingestion delay",
            },
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2222",
                    "title": "Research invoice matching",
                    "state": {"name": "ToResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2222",
                "title": "Cursor researching: Research invoice matching",
            },
        )

    def test_supports_linear_changes_payloads(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"to": "state-id"}},
            "data": {
                "id": "issue-id",
                "identifier": "POI-3333",
                "title": "Map vendor requirements",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Map vendor requirements",
            },
        )

    def test_supports_structured_changed_field_entries(self):
        event = {
            "action": "update",
            "changedFields": [{"field": "workflowState"}],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Review handoff gaps",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Review handoff gaps",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4705",
            "title": "WRT orchestration in delivery transport emissions module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4705",
            "title": "WRT orchestration in delivery transport emissions module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Write up requirements",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-4705",
            "title": "cursor researching: WRT orchestration",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"}
            )
        )

    def test_cli_prints_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9999",
            "title": "Scope emissions work",
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
                "issueId": "POI-9999",
                "title": "Cursor researching: Scope emissions work",
            },
        )


if __name__ == "__main__":
    unittest.main()
