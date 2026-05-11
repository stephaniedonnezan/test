import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4658",
                "title": "Tidy up turn/ch4 seeders",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-4658",
                "title": "Tidy up turn/ch4 seeders",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4658",
                "title": "Cursor researching: Tidy up turn/ch4 seeders",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "type": "statusChanged",
            "new_status": "toResearch",
            "issueId": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Tidy up turn/ch4 seeders",
        )

    def test_uses_nested_state_name_for_status(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Tidy up turn/ch4 seeders",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4658",
            "title": "Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4658",
            "title": "cursor researching: Tidy up turn/ch4 seeders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4658"}
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
