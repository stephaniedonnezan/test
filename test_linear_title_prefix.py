import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_when_status_changes_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4534",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4534",
                "title": "Cursor researching: Block closed mass balance energy price edits",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4534",
                "title": "Block closed mass balance energy price edits",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Block closed mass balance energy price edits",
        )

    def test_accepts_linear_data_issue_payload(self):
        event = {
            "type": "Issue",
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4534",
                    "title": "Block closed mass balance energy price edits",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4534",
                "title": "Cursor researching: Block closed mass balance energy price edits",
            },
        )

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "status-changed",
            "new_status": "toResearch",
            "issueId": "POI-4534",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Block closed mass balance energy price edits",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4534",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4534",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4534",
            "title": "cursor researching: Block closed mass balance energy price edits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4534",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "status": "To Research",
            "id": "POI-4534",
            "title": "Block closed mass balance energy price edits",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Block closed mass balance energy price edits",
        )


if __name__ == "__main__":
    unittest.main()
