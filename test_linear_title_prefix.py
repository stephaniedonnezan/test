import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_for_to_research_status(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4646",
                    "title": '[]"timezone" acting as a filter in the "container events" tab',
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4646",
                "title": 'Cursor researching: []"timezone" acting as a filter in the "container events" tab',
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4646",
                "title": "Timezone filter issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4646",
                "title": "Timezone filter issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4646",
            "title": "cursor researching: Timezone filter issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4646",
                "title": "Timezone filter issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4646",
                "title": "Cursor researching: Timezone filter issue",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4646",
                "title": "Timezone filter issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4646",
            "title": "Timezone filter issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4646",
                "title": "Cursor researching: Timezone filter issue",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )


if __name__ == "__main__":
    unittest.main()
