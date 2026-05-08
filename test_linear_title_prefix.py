import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4503",
            "title": "Trader site unable to close mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4503",
                "title": "Cursor researching: Trader site unable to close mass balance",
            },
        )

    def test_uses_nested_trigger_context_from_automation_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4503",
                "title": "Trader site unable to close mass balance",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4503",
                "title": "Cursor researching: Trader site unable to close mass balance",
            },
        )

    def test_accepts_nested_issue_payload(self):
        event = {
            "type": "statusChanged",
            "status": "to_research",
            "data": {
                "issue": {
                    "identifier": "POI-4503",
                    "title": "Trader site unable to close mass balance",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4503",
                "title": "Cursor researching: Trader site unable to close mass balance",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "state": {"name": "To Research"},
            "issueId": "POI-4503",
            "title": "Trader site unable to close mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4503",
                "title": "Cursor researching: Trader site unable to close mass balance",
            },
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "triggerType": "comment_created",
            "newStatus": "to research",
            "id": "POI-4503",
            "title": "Trader site unable to close mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4503",
            "title": "Trader site unable to close mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "to research",
            "id": "POI-4503",
            "title": "cursor researching: Trader site unable to close mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "to research",
            "title": "Trader site unable to close mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "triggerType": "status_changed",
            "newStatus": "to research",
            "id": "POI-4503",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
