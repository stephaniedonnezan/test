import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3499",
                "title": "Turn cross site data into a class",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3499",
                "title": "Cursor researching: Turn cross site data into a class",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3499",
                "title": "Turn cross site data into a class",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3499",
                "title": "Turn cross site data into a class",
            }
        )

        self.assertIsNone(result)

    def test_avoids_duplicate_prefixes(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3499",
                "title": "cursor researching: Turn cross site data into a class",
            }
        )

        self.assertIsNone(result)

    def test_handles_nested_linear_payloads(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-3499",
                    "title": "Turn cross site data into a class",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3499",
                "title": "Cursor researching: Turn cross site data into a class",
            },
        )

    def test_requires_status_field_for_generic_update_events(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "data": {
                    "identifier": "POI-3499",
                    "title": "Turn cross site data into a class",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
