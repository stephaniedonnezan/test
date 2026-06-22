import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handleIssueStatusChanged,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Add a report export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Add a report export",
            },
        )

    def test_prefixes_cloud_automation_trigger_context_event(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4575",
                    "title": (
                        "Mass balance export: Use Mass Balance page from "
                        "non-container logic for the container logic"
                    ),
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4575",
                "title": (
                    "Cursor researching: Mass balance export: Use Mass Balance page from "
                    "non-container logic for the container logic"
                ),
            },
        )

    def test_supports_camel_case_status_changed_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-124",
            "title": "Handle audit logs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Handle audit logs",
            },
        )

    def test_prefixes_nested_linear_issue_updated_event(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-125",
                "title": "Investigate traceability checks",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-125",
                "title": "Cursor researching: Investigate traceability checks",
            },
        )

    def test_prefers_nested_issue_id_over_outer_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-125",
                "title": "Investigate traceability checks",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-125",
                "title": "Cursor researching: Investigate traceability checks",
            },
        )

    def test_uses_changed_status_target_value(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "identifier": "POI-126",
                "title": "Research trader scope",
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-126",
                "title": "Cursor researching: Research trader scope",
            },
        )

    def test_uses_changed_status_target_from_list(self):
        event = {
            "webhookType": "updated_issue",
            "issue": {
                "key": "POI-127",
                "title": "Document hydrogen purchase rules",
            },
            "changes": [
                {
                    "field": "status",
                    "newValue": {"name": "to_research"},
                }
            ],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-127",
                "title": "Cursor researching: Document hydrogen purchase rules",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4575",
            "title": "Do not prefix this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_unrelated_trigger_even_with_new_status_field(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-129",
            "title": "Do not prefix this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-130",
                "title": "Do not prefix this",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-131",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-132",
                    "title": "  ",
                }
            )
        )

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a mapping"))

    def test_compatibility_wrappers_delegate_to_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issue_id": "POI-133",
            "title": "Wrap the handler",
        }
        expected = {
            "action": "update_issue_title",
            "issueId": "POI-133",
            "title": "Cursor researching: Wrap the handler",
        }

        self.assertEqual(handle_issue_status_changed(event), expected)
        self.assertEqual(handleIssueStatusChanged(event), expected)


if __name__ == "__main__":
    unittest.main()
