import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5102",
                "title": "Phase 1: Backend",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Phase 1: Backend",
            },
        )

    def test_prefixes_nested_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-5102",
                    "title": "Research title behavior",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Research title behavior",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-5102",
            "title": "Normalize values",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Normalize values",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5102",
            "title": "Phase 1: Backend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5102",
            "title": "Phase 1: Backend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-5102",
                "title": "Phase 1: Backend",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_status_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-5102",
                    "title": "Phase 1: Backend",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Phase 1: Backend",
            },
        )

    def test_reads_changed_status_before_stale_issue_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"from": "In Progress", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-5102",
                    "title": "Use changed status",
                    "status": "In Progress",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Use changed status",
            },
        )

    def test_reads_changed_state_object(self):
        event = {
            "action": "update",
            "webhookType": "issue",
            "updatedFields": ["workflowState"],
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "data": {"id": "POI-5102", "title": "Workflow state"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5102",
                "title": "Cursor researching: Workflow state",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5102",
            "title": "cursor researching: Phase 1: Backend",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "data": {"issue": {"state": {"name": "To Research"}}},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
