import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_automation_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Audit invite flow",
                "id": "POI-4064",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4064",
                "title": "Cursor researching: Audit invite flow",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Audit invite flow",
                "id": "POI-4064",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "Audit invite flow",
                "id": "POI-4064",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "cursor researching: Audit invite flow",
                "id": "POI-4064",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "title": " Audit invite flow ",
            "issueId": "POI-4064",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4064",
                "title": "Cursor researching: Audit invite flow",
            },
        )

    def test_supports_linear_issue_updated_payloads(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "state": {"name": "To Research"},
            "identifier": "POI-4064",
            "title": "Audit invite flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4064",
                "title": "Cursor researching: Audit invite flow",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4064"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Audit invite flow",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
