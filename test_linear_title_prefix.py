import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch meter readings once",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance: fetch meter readings once",
            },
        )

    def test_builds_update_for_full_automation_trigger_wrapper(self):
        event = {
            "automationId": "automation-1",
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4965",
                    "title": "Grid mix calculation",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Grid mix calculation",
            },
        )

    def test_normalizes_status_separators_and_camel_case_triggers(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4965",
            "title": "Research status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Research status",
            },
        )

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "internal-linear-id",
                "identifier": "POI-4965",
                "title": "Nested issue title",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_accepts_workflow_state_name(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog"}},
            "issue": {
                "identifier": "POI-4965",
                "title": "Workflow state issue",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Workflow state issue",
            },
        )

    def test_reads_new_status_from_change_objects(self):
        event = {
            "action": "update",
            "changes": [{"field": "status", "newValue": "To Research"}],
            "payload": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Changed status issue",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Changed status issue",
            },
        )

    def test_uses_current_state_when_updated_from_marks_state_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "Updated from state issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Updated from state issue",
            },
        )

    def test_ignores_non_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4965",
            "title": "Already done",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_event(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4965",
                "title": "Title changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": " to research ",
            "issue_id": " POI-4965 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
