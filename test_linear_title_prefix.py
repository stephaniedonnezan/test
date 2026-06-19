import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4009",
                "title": "Add Select field on Delivery Form",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Add Select field on Delivery Form",
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4009",
                    "title": "Investigate delivery form",
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate delivery form")

    def test_accepts_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-4009",
                    "title": "Investigate batch amount copy",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4009",
                "title": "Cursor researching: Investigate batch amount copy",
            },
        )

    def test_normalizes_status_casing_separators_and_camel_case(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "toResearch",
                "issueId": "POI-4009",
                "title": "Research status formatting",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Research status formatting")

    def test_ignores_non_research_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4009",
                "title": "Add Select field on Delivery Form",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_trigger(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4009",
                "title": "Add Select field on Delivery Form",
            }
        )

        self.assertIsNone(result)

    def test_ignores_generic_updates_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "data": {
                    "identifier": "POI-4009",
                    "title": "Add Select field on Delivery Form",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4009",
                "title": "cursor researching: Add Select field on Delivery Form",
            }
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
