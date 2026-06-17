import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4964",
                "title": (
                    "Cursor researching: "
                    "Invite link not showing after user is invited"
                ),
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4964",
                "title": "Invite link not showing after user is invited",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Invite link not showing after user is invited",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4964",
            "title": "Invite link not showing after user is invited",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4964",
            "title": "Cursor researching: Invite link not showing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "ToResearch",
            "identifier": "POI-4964",
            "title": "Invite link not showing",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Invite link not showing",
        )

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4964",
                    "title": "Invite link not showing",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4964",
                "title": "Cursor researching: Invite link not showing",
            },
        )

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4964",
                    "title": "Invite link not showing",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_required_issue_data_is_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Invite link not showing",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
