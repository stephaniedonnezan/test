import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4208",
                "title": "Cursor researching: Gather Day ahead grid price from ENTSO",
            },
        )

    def test_uses_nested_trigger_context_from_automation_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4208",
                "title": "Gather Day ahead grid price from ENTSO",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4208",
                "title": "Cursor researching: Gather Day ahead grid price from ENTSO",
            },
        )

    def test_accepts_linear_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4208",
                    "title": "Gather Day ahead grid price from ENTSO",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4208",
                "title": "Cursor researching: Gather Day ahead grid price from ENTSO",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "state": {"name": "To Research"},
            "issueId": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather Day ahead grid price from ENTSO",
        )

    def test_accepts_action_status_changed_when_webhook_type_is_issue(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to-research",
            "issueId": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather Day ahead grid price from ENTSO",
        )

    def test_accepts_update_action_when_status_field_changed(self):
        event = {
            "action": "update",
            "updated_fields": {"status": {"old": "Backlog", "new": "To Research"}},
            "status": "To Research",
            "issueId": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather Day ahead grid price from ENTSO",
        )

    def test_accepts_nested_workflow_state_status(self):
        event = {
            "trigger": "status_changed",
            "workflowState": {"name": "toResearch"},
            "issueId": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather Day ahead grid price from ENTSO",
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_updated_when_status_field_was_not_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-4208",
            "title": "Gather Day ahead grid price from ENTSO",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4208",
            "title": "cursor researching: Gather Day ahead grid price from ENTSO",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-4208",
            "title": "  Gather Day ahead grid price from ENTSO  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather Day ahead grid price from ENTSO",
        )

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Gather Day ahead grid price from ENTSO",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4208",
                }
            )
        )

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
