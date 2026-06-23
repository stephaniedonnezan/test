import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4696",
            "title": "WP4 - ProcessingUnitStrategy + factory wiring",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4696",
                "title": "Cursor researching: WP4 - ProcessingUnitStrategy + factory wiring",
            },
        )

    def test_nested_cursor_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4696",
                    "title": "Investigate title automation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4696",
                "title": "Cursor researching: Investigate title automation",
            },
        )

    def test_status_normalization_accepts_separators_and_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-123",
            "title": "Normalize status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Normalize status",
            },
        )

    def test_generic_issue_update_requires_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-123",
            "title": "Only title changed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_with_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "status": "To Research",
            "identifier": "POI-123",
            "title": "Status changed",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Status changed",
            },
        )

    def test_changed_fields_mapping_supplies_new_status(self):
        event = {
            "action": "update",
            "updatedFields": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "id": "POI-123",
            "title": "Mapping change",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Mapping change",
            },
        )

    def test_linear_changes_mapping_supplies_new_status(self):
        event = {
            "action": "update",
            "changes": {
                "workflowState": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Nested Linear issue",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_matching_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Backlog",
            "id": "POI-123",
            "title": "Not ready",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
