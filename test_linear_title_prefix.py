import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3778",
            "title": "Add GHG and saving calculations to the Excel sheet",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3778",
                "title": "Cursor researching: Add GHG and saving calculations to the Excel sheet",
            },
        )

    def test_supports_cursor_automation_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3778",
                "title": "Add GHG and saving calculations to the Excel sheet",
            }
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-3778")
        self.assertEqual(
            result["title"],
            "Cursor researching: Add GHG and saving calculations to the Excel sheet",
        )

    def test_supports_linear_issue_updated_payload_when_status_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Research export requirements",
                    "state": {"name": "To_Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research export requirements",
            },
        )

    def test_supports_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-456",
            "title": "Review research scope",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Review research scope",
            },
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-789",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_without_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "id": "POI-789",
            "status": "to research",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Duplicate",
            "id": "POI-3778",
            "title": "Add GHG and saving calculations to the Excel sheet",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3778",
            "title": "cursor researching: Add GHG and saving calculations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Add GHG and saving calculations",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3778",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
