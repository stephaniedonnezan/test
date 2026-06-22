import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3765",
            "title": "[][Dev] - Refine Site Details>KPIs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3765",
                "title": "Cursor researching: [][Dev] - Refine Site Details>KPIs",
            },
        )

    def test_supports_nested_cursor_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-100",
                "title": "Research supplier dashboard",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Research supplier dashboard",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-3765",
            "title": "[][Dev] - Refine Site Details>KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3765",
            "title": "[][Dev] - Refine Site Details>KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3765",
            "title": "cursor researching: [][Dev] - Refine Site Details>KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-200",
            "title": "Audit-period KPI cards",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-200",
                "title": "Cursor researching: Audit-period KPI cards",
            },
        )

    def test_supports_nested_linear_issue_update_with_updated_from_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-300",
                "title": "Mass balance KPI overview",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"state": {"name": "Backlog"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-300",
                "title": "Cursor researching: Mass balance KPI overview",
            },
        )

    def test_supports_change_payloads_with_new_status_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "identifier": "POI-400",
                "title": "Company overview KPI cards",
            },
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-400",
                "title": "Cursor researching: Company overview KPI cards",
            },
        )

    def test_ignores_generic_issue_updates_without_status_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-500",
                "title": "KPI layout polish",
                "state": {"name": "To Research"},
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-600",
                }
            )
        )

    def test_supports_workflow_state_names(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-700",
                "title": "Workflow state payload",
                "workflowState": {"name": "To Research"},
            },
            "updatedFields": ["workflowState"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-700",
                "title": "Cursor researching: Workflow state payload",
            },
        )

    def test_cli_reads_json_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "identifier": "POI-800",
            "title": "CLI payload",
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
                "issueId": "POI-800",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
