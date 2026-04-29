import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4583",
                "title": "Issue with Export XLS button",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Issue with Export XLS button",
            },
        )

    def test_supports_flat_payloads(self):
        event = {
            "trigger": "status changed",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate export",
            },
        )

    def test_supports_nested_data_issue_payloads(self):
        event = {
            "action": "statusChanged",
            "data": {
                "newStatus": "To Research",
                "issue": {
                    "id": "POI-2",
                    "title": "Check container search",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check container search",
            },
        )

    def test_uses_state_name_when_status_is_nested(self):
        event = {
            "trigger": "status_changed",
            "id": "POI-3",
            "title": "Add dropdown search",
            "state": {"name": "To Research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Add dropdown search",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_data(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "Outer title",
            },
            "data": {
                "issue": {
                    "id": "POI-ignored",
                    "title": "Nested title",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_does_not_prefix_for_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5",
            "title": "Leave unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_prefix_for_other_trigger(self):
        event = {
            "trigger": "issue_created",
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "Leave unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
            "title": "Cursor researching: Existing research title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "cursor Researching: Existing research title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "  Needs research  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Needs research",
            },
        )

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "No id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-10",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
