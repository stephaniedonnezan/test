import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handleIssueStatusChanged,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_trigger_context_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4605",
                "title": "Check delivery locking behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4605",
                "title": "Cursor researching: Check delivery locking behavior",
            },
        )

    def test_supports_flat_status_changed_payloads(self):
        event = {
            "type": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "Research flat payload",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research flat payload",
            },
        )

    def test_supports_nested_linear_issue_payloads(self):
        event = {
            "action": "statusChanged",
            "data": {
                "state": {"name": "To Research"},
                "issue": {
                    "identifier": "POI-456",
                    "title": "Nested Linear issue",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Created issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-123",
            "title": "Done issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))

    def test_handler_aliases_match_primary_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Aliased handler",
        }
        expected = {
            "action": "update_issue_title",
            "issueId": "POI-123",
            "title": "Cursor researching: Aliased handler",
        }

        self.assertEqual(handle_issue_status_changed(event), expected)
        self.assertEqual(handleIssueStatusChanged(event), expected)


if __name__ == "__main__":
    unittest.main()
