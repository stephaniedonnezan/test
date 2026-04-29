import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4530",
                    "title": "[UBA specific fields in Atmen] Trader Site",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4530",
                "title": "Cursor researching: [UBA specific fields in Atmen] Trader Site",
            },
        )

    def test_accepts_flat_payloads(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4530",
                "title": "Investigate UBA fields",
            }
        )

        self.assertEqual(result["issueId"], "POI-4530")
        self.assertEqual(result["title"], "Cursor researching: Investigate UBA fields")

    def test_accepts_issue_id_when_id_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-4530",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-4530")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to research",
                    "id": "POI-4530",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate UBA fields")

    def test_matches_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "STATUS-CHANGED",
                    "newStatus": "To_Research",
                    "id": "POI-4530",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate UBA fields")

    def test_skips_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Agent research to review",
                    "id": "POI-4530",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-4530",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_existing_prefix_case_insensitively(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4530",
                    "title": "cursor researching: Investigate UBA fields",
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
                    "id": "POI-4530",
                    "title": "  Investigate UBA fields  ",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate UBA fields")

    def test_skips_blank_title(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4530",
                    "title": "   ",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_missing_issue_id(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Investigate UBA fields",
                }
            }
        )

        self.assertIsNone(result)

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
