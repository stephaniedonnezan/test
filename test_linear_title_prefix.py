import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_status_changed_payload_adds_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3672",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_nested_trigger_context_payload_adds_prefix(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-123",
                "title": "Investigate report drift",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate report drift",
            },
        )

    def test_linear_data_issue_payload_adds_prefix(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Clarify audit export",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Clarify audit export",
            },
        )

    def test_changed_workflow_state_payload_adds_prefix(self):
        event = {
            "type": "update",
            "changedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Research certificate evidence",
                    "workflowState": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research certificate evidence",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-789",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-789",
            "title": "Reviewed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-789",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-789",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
