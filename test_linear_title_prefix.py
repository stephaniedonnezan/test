import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4545",
            "title": "[Container Logic MB] Deliveries connected to batches outside of site",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": (
                    "Cursor researching: [Container Logic MB] Deliveries connected "
                    "to batches outside of site"
                ),
            },
        )

    def test_builds_update_for_cursor_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4545",
                "title": "Delivery links need research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery links need research",
            },
        )

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4545",
            "title": "Delivery links need research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery links need research",
            },
        )

    def test_normalizes_status_separators_and_case(self):
        event = {
            "trigger": "STATUS_CHANGED",
            "new_status": "TO_RESEARCH",
            "identifier": "POI-4545",
            "title": "Delivery links need research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery links need research",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4545",
            "title": "Delivery links need research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4545",
            "title": "Delivery links need research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4545",
            "title": "cursor researching: Delivery links need research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4545",
                    "title": "Delivery links need research",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery links need research",
            },
        )

    def test_uses_changed_status_value_from_update_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4545",
                    "title": "Delivery links need research",
                    "status": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4545",
                "title": "Cursor researching: Delivery links need research",
            },
        )

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4545",
                    "title": "Delivery links need research",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4545"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Delivery links need research",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
