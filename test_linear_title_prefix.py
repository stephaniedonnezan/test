import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_to_research_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5058",
                "title": "Move the `mb-data-manager` into the psqo module",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the `mb-data-manager` into the psqo module",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-5058",
            "title": "Move data manager",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5058",
            "title": "Move data manager",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-5058",
            "title": "cursor researching: Move data manager",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "cursor researching: Move data manager",
            },
        )

    def test_accepts_normalized_status_spellings(self):
        event = {
            "trigger": "status-change",
            "new_status": "to_research",
            "identifier": "POI-5058",
            "title": "Move data manager",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move data manager",
            },
        )

    def test_accepts_nested_linear_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-internal-id",
                "identifier": "POI-5058",
                "title": "Move data manager",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move data manager",
            },
        )

    def test_prefers_nested_issue_id_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Move data manager",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Move data manager",
            },
        )

    def test_accepts_status_value_from_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "changes": {"status": {"newValue": {"name": "to-research"}}},
            "issueId": "POI-5058",
            "title": "Move data manager",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move data manager",
            },
        )

    def test_requires_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Move data manager",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
