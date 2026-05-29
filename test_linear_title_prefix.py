import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4772",
                    "title": "In the methane excel export, use 0 instead of N/A",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": "Cursor researching: In the methane excel export, use 0 instead of N/A",
            },
        )

    def test_matches_status_case_and_separator_variants(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "new_status": "To_Research",
                    "issueId": "POI-1",
                    "title": "Investigate export",
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Investigate export")

    def test_returns_none_for_other_statuses(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "DEV",
                        "id": "POI-2",
                        "title": "Implement export",
                    }
                }
            )
        )

    def test_returns_none_for_non_status_change_triggers(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "comment_created",
                        "newStatus": "to research",
                        "id": "POI-3",
                        "title": "Research export",
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
                        "id": "POI-4",
                        "title": "cursor researching: Research export",
                    }
                }
            )
        )

    def test_handles_nested_linear_issue_update_with_updated_fields(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "issue-id",
                        "identifier": "POI-5",
                        "title": "Nested issue",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_handles_nested_linear_issue_update_with_updated_from(self):
        update = build_issue_title_update(
            {
                "type": "Issue",
                "action": "Issue Updated",
                "updatedFrom": {"workflowState": {"name": "Backlog"}},
                "data": {
                    "issue": {
                        "identifier": "POI-6",
                        "title": "Workflow state issue",
                        "workflowState": {"name": "to-research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-6")
        self.assertEqual(update["title"], "Cursor researching: Workflow state issue")

    def test_ignores_generic_issue_update_without_status_field_change(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "action": "update",
                    "updatedFields": ["title"],
                    "data": {
                        "issue": {
                            "id": "POI-7",
                            "title": "Title changed",
                            "state": {"name": "to research"},
                        }
                    },
                }
            )
        )

    def test_trims_issue_id_and_title(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "identifier": " POI-8 ",
                    "title": "  Trim me  ",
                }
            }
        )

        self.assertEqual(update["issueId"], "POI-8")
        self.assertEqual(update["title"], "Cursor researching: Trim me")


if __name__ == "__main__":
    unittest.main()
