import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3106",
                "title": "Supply contract pos attributes",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3106",
                "title": "Cursor researching: Supply contract pos attributes",
            },
        )

    def test_builds_update_for_direct_payload(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Add hydrogen fixtures",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Add hydrogen fixtures",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2",
                "title": "Supply contract pos attributes",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "issueId": "POI-3",
            "title": "Comment-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-5",
            "title": "Camel case status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Camel case status",
            },
        )

    def test_builds_update_for_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "id": "POI-6",
                "title": "Nested Linear issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_ignores_non_status_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-7",
                "title": "Description changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_nested_issue_id_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "Issue Updated",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "id": "POI-10",
                "title": "Nested issue id",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: Nested issue id",
            },
        )

    def test_uses_identifier_and_trims_title(self):
        event = {
            "triggerContext": {
                "trigger": "state_changed",
                "newState": "To Research",
                "identifier": "POI-8",
                "title": "  Trim whitespace  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: Trim whitespace",
            },
        )

    def test_prioritizes_explicit_new_status_over_stale_nested_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issue": {
                "id": "POI-9",
                "title": "Explicit status wins",
                "status": "In Progress",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Explicit status wins",
            },
        )

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
