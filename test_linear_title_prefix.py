import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4573",
                    "title": "Random stock overflow on Turn2X Jan 2026",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_accepts_flat_payload(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-1",
                "title": "Investigate meter readings",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate meter readings")

    def test_accepts_separator_variants_in_status_and_trigger(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status-changed",
                    "newStatus": "to_research",
                    "id": "POI-2",
                    "title": "Check CO2 flow",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Check CO2 flow")

    def test_falls_back_to_status_when_new_status_missing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to research",
                    "id": "POI-3",
                    "title": "Confirm mass balance",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Confirm mass balance")

    def test_uses_issue_id_when_id_missing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-4",
                    "title": "Review inputs",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-4")

    def test_returns_none_for_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "In Progress",
                    "id": "POI-5",
                    "title": "Review inputs",
                }
            }
        )

        self.assertIsNone(result)

    def test_returns_none_for_other_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-6",
                    "title": "Review inputs",
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
                    "title": "Cursor researching: Review inputs",
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
                    "title": "cursor researching Review inputs",
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
                    "title": "  Review inputs  ",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Review inputs")

    def test_returns_none_when_issue_id_or_title_missing(self):
        missing_id = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Review inputs",
                }
            }
        )
        missing_title = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-10",
                }
            }
        )

        self.assertIsNone(missing_id)
        self.assertIsNone(missing_title)

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "an", "event"]))


if __name__ == "__main__":
    unittest.main()
