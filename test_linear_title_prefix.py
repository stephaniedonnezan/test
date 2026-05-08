import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4644",
            "title": "Investigate Sentry request failure",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Sentry request failure",
            },
        )

    def test_uses_nested_trigger_context_from_automation_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4644",
                "title": "Investigate Sentry request failure",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Sentry request failure",
            },
        )

    def test_accepts_nested_issue_payload(self):
        event = {
            "type": "statusChanged",
            "status": "to_research",
            "data": {
                "issue": {
                    "identifier": "POI-4644",
                    "title": "Investigate Sentry request failure",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Sentry request failure",
            },
        )

    def test_accepts_action_when_webhook_type_is_issue(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to-research",
            "issue": {
                "id": "POI-4644",
                "title": "Investigate Sentry request failure",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Sentry request failure",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "state": {"name": "To Research"},
            "issueId": "POI-4644",
            "title": "Investigate Sentry request failure",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: Investigate Sentry request failure",
            },
        )

    def test_skips_issue_updated_when_status_field_was_not_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-4644",
            "title": "Investigate Sentry request failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "Investigate Sentry request failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4644",
            "title": "Investigate Sentry request failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
            "title": "cursor researching: Investigate Sentry request failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Investigate Sentry request failure",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4644",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
