import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handleIssueStatusChanged,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4603",
                "title": "Delivery CSV Upload Update",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4603",
                "title": "Cursor researching: Delivery CSV Upload Update",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-1",
                    "title": "Nested payload",
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Nested payload")

    def test_accepts_linear_data_and_issue_payload_shape(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["workflowState"],
                "data": {
                    "issue": {
                        "identifier": "POI-2",
                        "title": "Issue data payload",
                        "workflowState": {"name": "to_research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Issue data payload",
            },
        )

    def test_outer_event_metadata_overrides_nested_payload(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-3",
                    "title": "Outer wins",
                },
                "newStatus": "to research",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Outer wins")

    def test_does_not_prefix_other_status_changes(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4603",
                "title": "Delivery CSV Upload Update",
            }
        )

        self.assertIsNone(update)

    def test_does_not_prefix_non_status_change_events(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4603",
                "title": "Delivery CSV Upload Update",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4603",
                "title": "cursor researching: Delivery CSV Upload Update",
            }
        )

        self.assertIsNone(update)

    def test_ignores_missing_issue_id_or_title(self):
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
                    "id": "POI-4603",
                }
            )
        )

    def test_handles_camel_case_status_and_trigger(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4",
                "title": "Camel case payload",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Camel case payload")

    def test_compatibility_wrappers_delegate_to_builder(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Wrapper payload",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))
        self.assertEqual(handleIssueStatusChanged(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
