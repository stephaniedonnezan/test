import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Improve qualified input storage",
                    "id": "POI-4107",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4107",
                "title": "Cursor researching: Improve qualified input storage",
            },
        )

    def test_ignores_other_statuses(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "title": "Improve qualified input storage",
                    "id": "POI-4107",
                }
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_events(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "title": "Improve qualified input storage",
                    "id": "POI-4107",
                }
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "title": "cursor researching: Improve qualified input storage",
                    "id": "POI-4107",
                }
            }
        )

        self.assertIsNone(update)

    def test_accepts_nested_linear_update_payloads(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "data": {
                    "updatedFields": ["state"],
                    "issue": {
                        "identifier": "POI-4107",
                        "title": "Improve qualified input storage",
                        "state": {"name": "To Research"},
                    },
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4107",
                "title": "Cursor researching: Improve qualified input storage",
            },
        )

    def test_requires_status_field_for_generic_update_payloads(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "data": {
                    "updatedFields": ["description"],
                    "issue": {
                        "identifier": "POI-4107",
                        "title": "Improve qualified input storage",
                        "state": {"name": "To Research"},
                    },
                },
            }
        )

        self.assertIsNone(update)

    def test_normalizes_status_and_trigger_casing(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "StatusChanged",
                    "newStatus": "to-research",
                    "title": "  Improve qualified input storage  ",
                    "id": " POI-4107 ",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4107",
                "title": "Cursor researching: Improve qualified input storage",
            },
        )

    def test_supports_workflow_state_name(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFrom": {"workflowState": "Backlog"},
                "issue": {
                    "id": "issue-id-1",
                    "title": "Review data model",
                    "workflowState": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "issue-id-1",
                "title": "Cursor researching: Review data model",
            },
        )


if __name__ == "__main__":
    unittest.main()
