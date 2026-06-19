import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-4249",
            "title": "cursor researching: Trader: Add dispatch date sanity check",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issue_id": "POI-4249",
            "title": "Trader: Add dispatch date sanity check",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "type": "Issue",
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "type": "Issue",
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_object(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"new": {"name": "To Research"}}},
            "issue": {
                "identifier": "POI-4249",
                "title": "Trader: Add dispatch date sanity check",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "state_changed",
            "toStatus": {"name": " to research "},
            "identifier": " POI-4249 ",
            "title": " Trader: Add dispatch date sanity check ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
