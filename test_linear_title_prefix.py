import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4619",
                "title": "Adjust global UI button",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4619",
                "title": "Cursor researching: Adjust global UI button",
            },
        )

    def test_status_matching_is_normalized(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": {"name": "To-Research"},
            "issueId": "POI-1",
            "title": "Normalize status labels",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Normalize status labels",
            },
        )

    def test_nested_linear_issue_payload_uses_issue_id_and_title(self):
        event = {
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "issue": {
                    "id": "nested-issue-id",
                    "title": "Investigate importer",
                    "state": {"name": "To Research"},
                }
            },
            "id": "webhook-event-id",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "nested-issue-id",
                "title": "Cursor researching: Investigate importer",
            },
        )

    def test_changed_fields_payload_can_provide_new_status(self):
        event = {
            "changedFields": ["status"],
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "issue": {"id": "POI-2", "title": "Research webhook changes"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research webhook changes",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Comment should not update title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4",
            "title": "Development issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
