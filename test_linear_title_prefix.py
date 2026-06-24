import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4865",
                "title": "Container canvas spotlight state missing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4865",
                "title": "Cursor researching: Container canvas spotlight state missing",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4865",
            "title": "cursor researching: Existing marker",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4865",
                "title": "cursor researching: Existing marker",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4865",
            "title": "Container canvas spotlight state missing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4865",
            "title": "Container canvas spotlight state missing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4865",
                    "title": "Container canvas spotlight state missing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4865",
                "title": "Cursor researching: Container canvas spotlight state missing",
            },
        )

    def test_prefixes_status_from_linear_changes(self):
        event = {
            "id": "webhook-event-id",
            "type": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "id": "issue-id",
                    "state": {"name": "Todo"},
                    "title": "Research follow-up",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Research follow-up",
            },
        )


if __name__ == "__main__":
    unittest.main()
