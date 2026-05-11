import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4438",
                    "title": "Container events parser",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4438",
                "title": "Cursor researching: Container events parser",
            },
        )

    def test_uses_nested_issue_data_with_outer_status_metadata(self):
        result = build_issue_title_update(
            {
                "type": "statusChanged",
                "new_status": "To Research",
                "data": {
                    "issue": {
                        "identifier": "POI-123",
                        "title": "Investigate imports",
                    }
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-123")
        self.assertEqual(result["title"], "Cursor researching: Investigate imports")

    def test_accepts_state_name_as_status(self):
        result = build_issue_title_update(
            {
                "action": "status-change",
                "state": {"name": "to_research"},
                "issueId": "POI-456",
                "title": "Check parser",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Check parser")

    def test_supports_issue_updated_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "webhookType": "Issue Updated",
                "updatedFields": [{"name": "workflowState"}],
                "workflowState": {"name": "To-Research"},
                "id": "POI-789",
                "title": "Review export",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Review export")

    def test_supports_status_updated_fields_without_trigger_name(self):
        result = build_issue_title_update(
            {
                "updatedFields": "status",
                "status": "toResearch",
                "id": "POI-790",
                "title": "Review upload",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Review upload")

    def test_ignores_non_status_change_events(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-111",
                "title": "A title",
            }
        )

        self.assertIsNone(result)

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-222",
                "title": "A title",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-333",
                "title": "cursor researching: A title",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        missing_title = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-444",
            }
        )
        missing_id = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "A title",
            }
        )

        self.assertIsNone(missing_title)
        self.assertIsNone(missing_id)

    def test_trims_issue_id_and_title(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": " to research ",
                "id": " POI-555 ",
                "title": " A title ",
            }
        )

        self.assertEqual(result["issueId"], "POI-555")
        self.assertEqual(result["title"], "Cursor researching: A title")

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
