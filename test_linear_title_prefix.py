import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4454",
            "title": "Clean up unused function",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4454",
                "title": "Cursor researching: Clean up unused function",
            },
        )

    def test_accepts_linear_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate webhook behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate webhook behavior",
            },
        )

    def test_reads_issue_details_from_linear_data_issue(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to_research",
            "data": {
                "issue": {
                    "identifier": "POI-234",
                    "title": "Map payload shape",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-234",
                "title": "Cursor researching: Map payload shape",
            },
        )

    def test_uses_state_name_as_status_fallback(self):
        event = {
            "trigger": "state_changed",
            "issueId": "POI-345",
            "title": "Use workflow state",
            "state": {"name": "toResearch"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-345",
                "title": "Cursor researching: Use workflow state",
            },
        )

    def test_accepts_issue_updated_event_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["priority", "status"],
            "newStatus": "To-Research",
            "id": "POI-456",
            "title": "Handle update webhook",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Handle update webhook",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-567",
            "title": "Not ready for research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-678",
            "title": "Comment only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_event_without_status_changed_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-789",
            "title": "Title only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-890",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        base_event = {
            "trigger": "status_changed",
            "newStatus": "to research",
        }

        self.assertIsNone(build_issue_title_update({**base_event, "title": "Missing id"}))
        self.assertIsNone(build_issue_title_update({**base_event, "id": "POI-901"}))


if __name__ == "__main__":
    unittest.main()
