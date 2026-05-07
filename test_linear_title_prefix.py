import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_for_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4162",
                "title": "Redesign evidence download subfolder structure by control category",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4162",
                "title": "Cursor researching: Redesign evidence download subfolder structure by control category",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4162",
                "title": "Redesign evidence download subfolder structure by control category",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4162",
                "title": "Redesign evidence download subfolder structure by control category",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4162",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_action_field_and_snake_case_status(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "new_status": "to_research",
            "data": {
                "issue": {
                    "identifier": "POI-4162",
                    "title": "Research title",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4162",
                "title": "Cursor researching: Research title",
            },
        )

    def test_accepts_state_name_as_status_fallback(self):
        event = {
            "type": "status_changed",
            "issueId": "POI-4162",
            "title": "Research title",
            "state": {"name": "to-research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4162",
                "title": "Cursor researching: Research title",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "status"],
            "status": "toResearch",
            "issue_id": "POI-4162",
            "title": "Research title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4162",
                "title": "Cursor researching: Research title",
            },
        )

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "title"],
            "status": "To Research",
            "id": "POI-4162",
            "title": "Research title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4162 ",
            "title": " Research title ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4162",
                "title": "Cursor researching: Research title",
            },
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
