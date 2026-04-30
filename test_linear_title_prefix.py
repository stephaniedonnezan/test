import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4571",
                "title": "Delivery 7846 certificate number",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4571",
                "title": "Cursor researching: Delivery 7846 certificate number",
            },
        )

    def test_accepts_flat_linear_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-123",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_accepts_nested_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-321",
                    "title": "Nested title",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Nested title",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            },
            "issue": {
                "id": "POI-456",
                "title": "Outer status wins",
                "state": {"name": "Done"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Outer status wins",
            },
        )

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "type": "status-changed",
            "new_status": "TO_RESEARCH",
            "id": "POI-789",
            "title": "Normalize me",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Normalize me",
            },
        )

    def test_uses_status_fallback_when_new_status_missing(self):
        event = {
            "webhookType": "statusChanged",
            "status": "To Research",
            "id": "POI-654",
            "title": "Fallback status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-654",
                "title": "Cursor researching: Fallback status",
            },
        )

    def test_uses_state_name_fallback(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-987",
            "title": "State fallback",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-987",
                "title": "Cursor researching: State fallback",
            },
        )

    def test_uses_identifier_when_id_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-111",
            "title": "Identifier only",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-111",
                "title": "Cursor researching: Identifier only",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-222",
            "title": "Cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-333",
            "title": "cursor researching - Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-444",
            "title": "Do not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-555",
            "title": "Do not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payloads_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-666",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
