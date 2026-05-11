import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "Fix the issue, make the test be green",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Fix the issue, make the test be green",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4666",
                "title": "Investigate UBA export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Investigate UBA export",
            },
        )

    def test_accepts_automation_trigger_context_shape(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Fix the issue, make the test be green",
                "id": "POI-4666",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Fix the issue, make the test be green",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4666",
                "title": "Investigate UBA export",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4666",
                "title": "Cursor researching: Investigate UBA export",
            },
        )

    def test_accepts_camel_case_status(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4666",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate UBA export",
        )

    def test_webhook_type_issue_does_not_mask_status_changed_action(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate UBA export",
        )

    def test_uses_state_name_when_status_is_nested(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4666",
            "title": "Investigate UBA export",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate UBA export",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4666",
            "title": "Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4666",
            "title": "Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4666",
            "title": "cursor researching: Investigate UBA export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4666"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
