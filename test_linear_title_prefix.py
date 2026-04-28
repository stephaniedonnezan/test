import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4418",
                    "title": "Create an Atmen Newsletter signup button",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4418",
                "title": "Cursor researching: Create an Atmen Newsletter signup button",
            },
        )

    def test_accepts_flat_payloads(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": "POI-123",
                "title": "Investigate support flow",
            }
        )

        self.assertEqual(result["issueId"], "POI-123")
        self.assertEqual(result["title"], "Cursor researching: Investigate support flow")

    def test_accepts_separator_and_case_variants(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "STATUS-CHANGED",
                    "newStatus": "To_Research",
                    "id": "POI-123",
                    "title": "Normalize status names",
                }
            }
        )

        self.assertIsNotNone(result)

    def test_falls_back_to_status_when_new_status_is_missing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status changed",
                    "status": "to research",
                    "id": "POI-123",
                    "title": "Fallback status field",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Fallback status field")

    def test_skips_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Unchanged",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Agent research to review",
                    "id": "POI-123",
                    "title": "Unchanged",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_titles_that_are_already_prefixed(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Cursor researching: Existing title",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_already_prefixed_titles_case_insensitively(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "cursor researching - Existing title",
                }
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            }
        )

        self.assertIsNone(result)

    def test_requires_title(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
