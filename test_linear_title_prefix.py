import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_flat_automation_status_change(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4200",
                    "title": "Allow Lhyfe to start on container logic",
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4200",
                "title": "Cursor researching: Allow Lhyfe to start on container logic",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-4200",
                    "title": "Issue title",
                },
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-4200",
                    "title": "Issue title",
                },
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-4200",
                    "title": "cursor researching: Issue title",
                },
            }
        )

        self.assertIsNone(result)

    def test_accepts_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "id": "linear-issue-id",
                    "identifier": "POI-4200",
                    "title": "Issue title",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_ignores_issue_updates_without_status_field_changes(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["description"],
                "data": {
                    "id": "linear-issue-id",
                    "title": "Issue title",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_accepts_status_separator_and_case_variants(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status-changed",
                    "newStatus": "toResearch",
                    "issueId": "POI-4200",
                    "title": "Issue title",
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Issue title")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Issue title",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4200",
                    }
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
