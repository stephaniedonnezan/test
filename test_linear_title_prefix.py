import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3763",
                "title": "Update the traceability deliveries download file template",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3763",
                "title": (
                    "Cursor researching: "
                    "Update the traceability deliveries download file template"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-3763",
                "title": "Update title",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3763",
                "title": "Update title",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "id": "POI-3763",
                "title": f"{TITLE_PREFIX}: Update title",
            }
        )

        self.assertIsNone(result)

    def test_matches_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issue_id": "POI-3763",
                "title": "Update title",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Update title")

    def test_supports_nested_trigger_context_payloads(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3763",
                    "title": "Update title",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-3763")

    def test_supports_linear_issue_updated_payload_with_updated_fields(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["status"],
                "data": {
                    "identifier": "POI-3763",
                    "title": "Update title",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Update title")

    def test_specific_action_is_used_when_webhook_type_is_generic(self):
        result = build_issue_title_update(
            {
                "webhookType": "issue",
                "action": "statusChanged",
                "status": "to research",
                "id": "POI-3763",
                "title": "Update title",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Update title")

    def test_ignores_issue_updated_payload_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description"],
                "data": {
                    "identifier": "POI-3763",
                    "title": "Update title",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3763"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Title"}
            )
        )

    def test_handler_alias_uses_same_behavior(self):
        result = handle_issue_status_changed(
            {
                "trigger": "stateChanged",
                "status": "to research",
                "id": "POI-3763",
                "title": "Update title",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Update title")


if __name__ == "__main__":
    unittest.main()
