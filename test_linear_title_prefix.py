import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4530",
                    "title": "UBA specific fields in Atmen",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4530",
                "title": "Cursor researching: UBA specific fields in Atmen",
            },
        )

    def test_accepts_flat_event_shape(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Investigate workflow",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate workflow")

    def test_accepts_issue_id_alias(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-2",
                    "title": "Add automation",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-2")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to research",
                    "id": "POI-3",
                    "title": "Check status fallback",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Check status fallback")

    def test_matches_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "STATUS-CHANGED",
                    "newStatus": "To_Research",
                    "id": "POI-4",
                    "title": "Normalize values",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Normalize values")

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5",
                    "title": "Cursor researching: Existing title",
                }
            }
        )

        self.assertIsNone(result)

    def test_existing_prefix_check_is_case_insensitive(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-6",
                    "title": "cursor researching - Existing title",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Todo",
                    "id": "POI-7",
                    "title": "Do not update",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-8",
                    "title": "Do not update",
                }
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        missing_id = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            }
        )
        missing_title = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-9",
                }
            }
        )

        self.assertIsNone(missing_id)
        self.assertIsNone(missing_title)

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
