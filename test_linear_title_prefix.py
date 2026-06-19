import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4033",
                "title": "Cursor researching: Adjust code for float operation issues",
            },
        )

    def test_ignores_status_change_to_done(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4033",
            "title": "Cursor researching: Adjust code for float operation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to_research",
            "id": "POI-4033",
            "title": "cursor RESEARCHING - Adjust code for float operation issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Adjust code for float operation issues")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to-research",
            "issue_id": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4033")

    def test_reads_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to research",
                    "id": "POI-4033",
                    "title": "Adjust code for float operation issues",
                }
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4033")
        self.assertEqual(
            result["title"],
            "Cursor researching: Adjust code for float operation issues",
        )

    def test_reads_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4033",
                "title": "Adjust code for float operation issues",
                "state": {"name": "To Research"},
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4033")
        self.assertEqual(
            result["title"],
            "Cursor researching: Adjust code for float operation issues",
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4033",
                "title": "Adjust code for float operation issues",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_change_record(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "identifier": "POI-4033",
            "title": "Adjust code for float operation issues",
        }

        result = build_issue_title_update(event)

        self.assertEqual(
            result["title"],
            "Cursor researching: Adjust code for float operation issues",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4033"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Adjust code for float operation issues",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
