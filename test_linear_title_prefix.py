import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
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
            "trigger": "statusChanged",
            "new_status": "To Research",
            "issueId": "POI-1",
            "title": "Investigate behavior",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate behavior",
            },
        )

    def test_supports_linear_action_and_nested_data(self):
        event = {
            "action": "statusChanged",
            "data": {
                "identifier": "POI-2",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_normalizes_status_separators(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-3",
            "title": "Underscored status",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Underscored status")

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Wrong trigger",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5",
            "title": "Wrong status",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "Cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "  Needs cleanup  ",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Needs cleanup")

    def test_outer_trigger_context_overrides_nested_issue_metadata(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "Outer title",
                "issue": {
                    "id": "POI-old",
                    "title": "Nested title",
                    "state": {"name": "Done"},
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_returns_none_for_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
