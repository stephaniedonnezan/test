import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3994",
                "title": "Make usage of decimal separators consistent",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3994",
                "title": "Cursor researching: Make usage of decimal separators consistent",
            },
        )

    def test_accepts_linear_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Review extracted document fields",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review extracted document fields",
            },
        )

    def test_accepts_updated_issue_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "status": "to-research",
            "issueId": "POI-124",
            "title": "Research a biomethane parser",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research a biomethane parser",
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3994",
                "title": "Make usage of decimal separators consistent",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-3994",
                "title": "Make usage of decimal separators consistent",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "new_status": "TO RESEARCH",
            "id": "POI-3994",
            "title": "cursor researching: Make usage of decimal separators consistent",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-3994",
            "title": "  Make usage of decimal separators consistent  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Make usage of decimal separators consistent",
        )

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Make usage of decimal separators consistent",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3994",
                }
            )
        )

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
