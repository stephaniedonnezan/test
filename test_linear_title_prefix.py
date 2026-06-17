import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Validate generated CSV against a live/sandbox Nabisy import",
                "id": "POI-4956",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4956",
                "title": "Cursor researching: Validate generated CSV against a live/sandbox Nabisy import",
            },
        )

    def test_ignores_non_status_trigger(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "comment_created",
                        "newStatus": "To Research",
                        "id": "POI-4956",
                        "title": "Validate generated CSV",
                    }
                }
            )
        )

    def test_ignores_other_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "In Progress",
                    "id": "POI-4956",
                    "title": "Validate generated CSV",
                }
            )
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4956",
                    "title": "cursor researching: Validate generated CSV",
                }
            )
        )

    def test_accepts_case_and_separator_variants(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "statusChanged",
                    "new_status": "to_research",
                    "issue_id": "POI-4956",
                    "title": "Validate generated CSV",
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-4956",
                "title": "Cursor researching: Validate generated CSV",
            },
        )

    def test_nested_linear_payload_uses_issue_identifier(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4956",
                "title": "Validate generated CSV",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4956",
                "title": "Cursor researching: Validate generated CSV",
            },
        )

    def test_generic_update_requires_status_change_metadata(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "type": "Issue",
                    "updatedFields": ["title"],
                    "data": {
                        "identifier": "POI-4956",
                        "title": "Validate generated CSV",
                        "state": {"name": "To Research"},
                    },
                }
            )
        )

    def test_reads_new_status_from_changes_map(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-4956",
                "title": "Validate generated CSV",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4956",
                "title": "Cursor researching: Validate generated CSV",
            },
        )

    def test_trims_title_and_issue_id(self):
        self.assertEqual(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "  POI-4956  ",
                    "title": "  Validate generated CSV  ",
                }
            ),
            {
                "action": "update_issue_title",
                "issueId": "POI-4956",
                "title": "Cursor researching: Validate generated CSV",
            },
        )

    def test_requires_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Validate generated CSV",
                }
            )
        )

    def test_requires_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4956",
                }
            )
        )

    def test_safely_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
