import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3655",
            "title": "Improve alert appearance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3655",
                "title": "Cursor researching: Improve alert appearance",
            },
        )

    def test_supports_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3655",
                "title": "[][Design Ticket] - Improve the Visual Appearance of Alerts",
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3655")
        self.assertEqual(
            update["title"],
            "Cursor researching: [][Design Ticket] - Improve the Visual Appearance of Alerts",
        )

    def test_supports_data_issue_payload_with_status_in_state(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-3655",
                    "title": "Improve alert appearance",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3655",
                "title": "Cursor researching: Improve alert appearance",
            },
        )

    def test_supports_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issueId": "POI-3655",
            "title": "Improve alert appearance",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "issueId": "POI-3655",
            "title": "Improve alert appearance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3655",
            "title": "Improve alert appearance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-3655",
            "title": "Improve alert appearance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3655",
            "title": "cursor researching: Improve alert appearance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "issue_id": " POI-3655 ",
            "title": " Improve alert appearance ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3655",
                "title": "Cursor researching: Improve alert appearance",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3655"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Improve alert appearance",
                }
            )
        )

    def test_alias_matches_entrypoint(self):
        self.assertIs(handle_issue_status_changed, build_issue_title_update)

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
