import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_accepts_trigger_context_payload_and_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4961",
                "title": "Remove Subscribe button on invite",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_uses_nested_linear_issue_data_for_generic_status_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "changes": {"state": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4961",
                    "title": "Remove Subscribe button on invite",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4961",
                "title": "Cursor researching: Remove Subscribe button on invite",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4961",
            "title": "Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
            "title": "cursor researching: Remove Subscribe button on invite",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4961",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
