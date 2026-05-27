import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4725",
                "title": "UX Design of delivery chains",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4725",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-100",
            "title": "Map delivery hops",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Map delivery hops",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-200",
            "title": "Build route editor",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-201",
            "title": "Build route editor",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-202",
            "title": "cursor researching: Build route editor",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-203",
                "title": "Design delivery chain overview",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Design delivery chain overview",
            },
        )

    def test_supports_workflow_state_name(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowStateId"],
            "data": {
                "identifier": "POI-204",
                "title": "Explore dependency graph UX",
                "workflowState": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-204",
                "title": "Cursor researching: Explore dependency graph UX",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-205",
                "title": "Explore dependency graph UX",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-206",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
