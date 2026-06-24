import unittest

from linear_title_prefix import build_issue_title_update, derive_updated_title


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4553",
            "title": "Add API to update document extraction results",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4553",
                "title": "Cursor researching: Add API to update document extraction results",
            },
        )

    def test_supports_cursor_automation_trigger_context_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-123",
                    "title": "Review supplier invoices",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review supplier invoices",
            },
        )

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Investigate biomethane document parsing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Investigate biomethane document parsing",
            },
        )

    def test_supports_status_from_changes_record(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "to_research"}},
            "issueId": "POI-789",
            "title": "Scope document extraction edits",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Scope document extraction edits",
            },
        )

    def test_accepts_camel_case_trigger_and_kebab_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "issue_id": "POI-321",
            "title": "Check title formatting",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-321",
                "title": "Cursor researching: Check title formatting",
            },
        )

    def test_derives_title_only(self):
        event = {
            "trigger": "state_changed",
            "newState": "To Research",
            "key": "POI-654",
            "title": "Research delivery route",
        }

        self.assertEqual(
            derive_updated_title(event),
            "Cursor researching: Research delivery route",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4553",
            "title": "Add API to update document extraction results",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4553",
            "title": "Add API to update document extraction results",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4553",
            "title": "Add API to update document extraction results",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4553",
            "title": "Cursor researching: Add API to update document extraction results",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4553",
            "title": "cursor researching Add API to update document extraction results",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-4553",
            "title": "  Add API to update document extraction results  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4553",
                "title": "Cursor researching: Add API to update document extraction results",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4553",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
