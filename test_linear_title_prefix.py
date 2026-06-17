import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4990",
                "title": "Error messages for importing need refinement",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4990",
                "title": "Cursor researching: Error messages for importing need refinement",
            },
        )

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4990",
                "title": "Import error copy",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Import error copy",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4990",
                "title": "Import error copy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4990",
                "title": "Import error copy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4990",
                "title": "cursor researching: Import error copy",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4990",
                "title": "Import error copy",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4990",
                "title": "Cursor researching: Import error copy",
            },
        )

    def test_supports_linear_updated_from_state_id_payload(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-status-id"},
            "data": {
                "identifier": "POI-4990",
                "title": "Import error copy",
                "state": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4990",
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4990",
                "title": "Import error copy",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identifier_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4990",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
