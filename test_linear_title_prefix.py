import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4518",
            "title": "Improve performance after the fix for POI-4469",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4518",
                "title": "Cursor researching: Improve performance after the fix for POI-4469",
            },
        )

    def test_accepts_linear_trigger_context_shape(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4518",
                "title": "Improve performance after the fix for POI-4469",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4518",
                "title": "Cursor researching: Improve performance after the fix for POI-4469",
            },
        )

    def test_accepts_nested_linear_data_issue_shape(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4518",
                    "title": "Improve performance after the fix for POI-4469",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4518",
                "title": "Cursor researching: Improve performance after the fix for POI-4469",
            },
        )

    def test_accepts_separator_and_case_variants(self):
        event = {
            "type": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-4518",
            "title": "  Improve performance after the fix for POI-4469  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4518",
                "title": "Cursor researching: Improve performance after the fix for POI-4469",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4518",
            "title": "Improve performance after the fix for POI-4469",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4518",
            "title": "Improve performance after the fix for POI-4469",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4518",
            "title": "cursor researching: Improve performance after the fix for POI-4469",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Improve performance after the fix for POI-4469",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4518",
            "title": "  ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
