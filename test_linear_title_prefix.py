import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_status_changed_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4587",
                "title": "Work to get the UBA template on Turn's H2 plant",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Work to get the UBA template on Turn's H2 plant",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4587",
                "title": "Work to get the UBA template on Turn's H2 plant",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4587",
                "title": "Work to get the UBA template on Turn's H2 plant",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4587",
                "title": "cursor researching: Work to get the UBA template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-4587",
            "title": "Investigate UBA template",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Investigate UBA template",
            },
        )

    def test_accepts_status_fallback_from_state_name(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "issue": {
                "id": "POI-4587",
                "title": "Investigate UBA template",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Investigate UBA template",
            },
        )

    def test_accepts_issue_updated_events_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "workflowState"],
            "workflowState": {"name": "to research"},
            "identifier": "POI-4587",
            "title": "Investigate UBA template",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Investigate UBA template",
            },
        )

    def test_ignores_issue_updated_events_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "newStatus": "to research",
            "identifier": "POI-4587",
            "title": "Investigate UBA template",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_data_issue_payload(self):
        event = {
            "data": {
                "action": "status_changed",
                "newStatus": "to research",
                "issue": {
                    "id": "POI-4587",
                    "title": "Investigate UBA template",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Investigate UBA template",
            },
        )

    def test_accepts_webhook_type_status_changed_payload(self):
        event = {
            "webhookType": "status_changed",
            "newStatus": "to research",
            "id": "POI-4587",
            "title": "Investigate UBA template",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4587",
                "title": "Cursor researching: Investigate UBA template",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Investigate UBA template",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4587",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
