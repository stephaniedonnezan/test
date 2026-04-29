import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4578",
                    "title": "Investigate container logic",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4578",
                "title": "Cursor researching: Investigate container logic",
            },
        )

    def test_supports_flat_trigger_context(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Flat payload",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Flat payload")

    def test_uses_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to research",
                    "id": "POI-2",
                    "title": "Fallback status",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Fallback status")

    def test_accepts_issue_id_when_id_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-3",
                    "title": "Issue id payload",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-3")

    def test_accepts_separator_variants_for_research_status(self):
        for status in ("to_research", "to-research", "  To   Research  "):
            with self.subTest(status=status):
                result = build_issue_title_update(
                    {
                        "triggerContext": {
                            "trigger": "status_changed",
                            "newStatus": status,
                            "id": "POI-4",
                            "title": "Separator variant",
                        }
                    }
                )

                self.assertEqual(
                    result["title"], "Cursor researching: Separator variant"
                )

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-5",
                    "title": "Wrong trigger",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_status_changes_to_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Todo",
                    "id": "POI-6",
                    "title": "Wrong status",
                }
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
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
                    "id": "POI-8",
                    "title": "cursor researching: Existing title",
                }
            }
        )

        self.assertIsNone(result)

    def test_trims_title_before_prefixing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-9",
                    "title": "  Needs research  ",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Needs research")

    def test_ignores_missing_required_issue_fields(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-10",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Missing id",
                    }
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a mapping"))


if __name__ == "__main__":
    unittest.main()
