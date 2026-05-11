import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_adds_cursor_researching_title_prefix_for_to_research_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4662",
                "title": "Fix exported UBA checkboxes",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4662",
                "title": "Cursor researching: Fix exported UBA checkboxes",
            },
        )

    def test_accepts_nested_linear_trigger_context_payload(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4662",
                    "title": "Investigate UBA export",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate UBA export")
        self.assertEqual(result["issueId"], "POI-4662")

    def test_accepts_status_changed_camel_case_and_status_fallback(self):
        result = handle_issue_status_changed(
            {
                "type": "statusChanged",
                "status": "toResearch",
                "issueId": "POI-4662",
                "title": "Research status automation",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Research status automation")

    def test_accepts_issue_updated_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": ["description", "state"],
                "state": {"name": "to-research"},
                "identifier": "POI-4662",
                "title": "State changed payload",
            }
        )

        self.assertEqual(result["issueId"], "POI-4662")
        self.assertEqual(result["title"], "Cursor researching: State changed payload")

    def test_ignores_issue_updated_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": ["description"],
                "status": "to research",
                "id": "POI-4662",
                "title": "Description changed only",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_to_research_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4662",
                "title": "Fix exported UBA checkboxes",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_trigger(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4662",
                "title": "Fix exported UBA checkboxes",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4662",
                "title": "cursor researching: Fix exported UBA checkboxes",
            }
        )

        self.assertIsNone(result)

    def test_ignores_payloads_without_required_issue_fields(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4662",
                }
            )
        )
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
