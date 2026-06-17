import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_accepts_full_automation_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_accepts_changed_status_value(self):
        event = {
            "type": "Issue Updated",
            "changedFields": "title,status",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_ignores_status_changed_to_another_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_when_status_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-4969",
            "title": "Unexpected star icon when linking deliveries",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issue_id": "POI-4969",
            "title": "cursor researching: Unexpected star icon when linking deliveries",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {"trigger": "status_changed", "newStatus": "To Research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
