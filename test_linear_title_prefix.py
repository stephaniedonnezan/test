import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4969",
                "title": "cursor researching: Unexpected star icon when linking deliveries",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "new_status": "To-Research",
                "id": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Unexpected star icon when linking deliveries",
        )

    def test_prefixes_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4969",
                "title": "Cursor researching: Unexpected star icon when linking deliveries",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_explicit_new_status_over_previous_status_values(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "newStatus": "To Research",
            "updatedFrom": {"status": "Backlog"},
            "data": {
                "identifier": "POI-4969",
                "title": "Unexpected star icon when linking deliveries",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4969",
        )

    def test_returns_none_when_issue_title_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4969",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
