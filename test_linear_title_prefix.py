import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5058",
            "title": "Move the mb-data-manager into the psqo module",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_reads_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Investigate export drift",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate export drift",
            },
        )

    def test_reads_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Check assisted database output",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Check assisted database output",
            },
        )

    def test_reads_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "issue": {"key": "POI-789", "title": "Review data provider move"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review data provider move",
            },
        )

    def test_reads_status_from_changes_list(self):
        event = {
            "webhookType": "issue_updated",
            "changes": [
                {
                    "fieldName": "status",
                    "newValue": "to-research",
                }
            ],
            "issueId": "POI-321",
            "title": "Audit hydrogen strategy coupling",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Audit hydrogen strategy coupling",
            },
        )

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5058",
            "title": "Move the mb-data-manager into the psqo module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-5058",
            "title": "Move the mb-data-manager into the psqo module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-5058",
            "title": "cursor researching: Move the mb-data-manager into the psqo module",
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
                    "id": "POI-5058",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
