import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4600",
                "title": "Potential rounding errors",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4600",
                "title": "Cursor researching: Potential rounding errors",
            },
        )

    def test_normalizes_status_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate something",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate something",
            },
        )

    def test_uses_nested_issue_payload_and_workflow_state(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue title",
                    "workflowState": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_supports_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["priority", "state"],
            "status": {"name": "To Research"},
            "id": "POI-3",
            "title": "Updated issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Updated issue",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-7",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-8",
                    "title": "   ",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
