import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3672",
                "title": "CI KPIs on the site management page are wrong",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_prefixes_title_for_cursor_automation_trigger_context(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-1",
                    "title": "Investigate data drift",
                },
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Investigate data drift")
        self.assertEqual(update["issueId"], "POI-1")

    def test_accepts_linear_issue_updated_payload_when_status_field_changed(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-2",
                        "title": "Add export validation",
                        "state": {"name": "to-research"},
                    }
                },
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Add export validation")
        self.assertEqual(update["issueId"], "POI-2")

    def test_accepts_status_changed_camel_case_and_new_status_alias(self):
        update = build_issue_title_update(
            {
                "triggerType": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-3",
                "title": "Fix import warning",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Fix import warning")

    def test_accepts_status_changed_action_when_webhook_type_is_issue(self):
        update = build_issue_title_update(
            {
                "webhookType": "issue",
                "action": "status_changed",
                "status": "to research",
                "issue_id": "POI-9",
                "title": "Handle action payload",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Handle action payload")

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "cursor researching: Existing title",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_event(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "Respond to question",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "in progress",
                "id": "POI-6",
                "title": "Build feature",
            }
        )

        self.assertIsNone(update)

    def test_ignores_issue_updated_when_status_field_did_not_change(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["title"],
                "status": "to research",
                "id": "POI-7",
                "title": "Rename issue",
            }
        )

        self.assertIsNone(update)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-8",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
