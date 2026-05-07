import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_trigger_context_research_status(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4257",
                "title": "Add search bar in batch selection dropdown list",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4257",
                "title": (
                    "Cursor researching: "
                    "Add search bar in batch selection dropdown list"
                ),
            },
        )

    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-123",
            "title": "Assess API behavior",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Assess API behavior",
            },
        )

    def test_uses_state_name_when_new_status_is_missing(self):
        event = {
            "trigger": "status-changed",
            "state": {"name": "ToResearch"},
            "id": "POI-124",
            "title": "Review matching flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Review matching flow",
            },
        )

    def test_handles_issue_updated_payload_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "identifier": "POI-125",
                    "title": "Research importer edge cases",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-125",
                "title": "Cursor researching: Research importer edge cases",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-126",
            "title": "Add search bar",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-127",
            "title": "Assess comment trigger",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_updated_fields_on_unrelated_trigger(self):
        event = {
            "trigger": "comment_created",
            "updatedFields": ["status"],
            "newStatus": "to research",
            "id": "POI-130",
            "title": "Assess comment update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-128",
            "title": "cursor researching: Assess title prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Assess title prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-129",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
