import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_when_status_changes_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4385",
                    "title": "Create a validation",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4385",
                "title": "Cursor researching: Create a validation",
            },
        )

    def test_accepts_flat_trigger_context(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": "POI-4385",
                "title": "Investigate overlap validation",
            }
        )

        self.assertEqual(result["issueId"], "POI-4385")
        self.assertEqual(
            result["title"],
            "Cursor researching: Investigate overlap validation",
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to_research",
                    "id": "POI-4385",
                    "title": "Review requirements",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Review requirements")

    def test_ignores_non_status_changed_triggers(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "comment_created",
                        "newStatus": "to research",
                        "id": "POI-4385",
                        "title": "Create a validation",
                    }
                }
            )
        )

    def test_ignores_other_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "In Review",
                        "id": "POI-4385",
                        "title": "Create a validation",
                    }
                }
            )
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4385",
                        "title": "Cursor researching: Create a validation",
                    }
                }
            )
        )

    def test_existing_prefix_check_is_case_insensitive(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4385",
                        "title": "cursor researching - Create a validation",
                    }
                }
            )
        )

    def test_trims_title_before_prefixing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4385",
                    "title": "  Create a validation  ",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Create a validation")

    def test_ignores_missing_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Create a validation",
                    }
                }
            )
        )

    def test_ignores_blank_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4385",
                        "title": "   ",
                    }
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
