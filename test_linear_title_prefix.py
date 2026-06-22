import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch the meter readings only once",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": (
                    "Cursor researching: performance: fetch the meter readings only once"
                ),
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4965",
            "title": "performance: fetch the meter readings only once",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "performance: fetch the meter readings only once",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "trigger": "statusChanged",
            "status": "To Research",
            "identifier": "POI-4965",
            "title": "Cursor researching: performance work",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance work",
            },
        )

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-4965",
            "title": "cursor researching: performance work",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: performance work",
        )

    def test_normalizes_camel_case_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "identifier": "POI-4965",
            "title": "performance work",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: performance work",
        )

    def test_normalizes_separator_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "identifier": "POI-4965",
            "title": "performance work",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: performance work",
        )

    def test_handles_cursor_automation_trigger_context_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4965",
                    "title": "performance work",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance work",
            },
        )

    def test_handles_top_level_trigger_context_wrapper(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4965",
                "title": "performance work",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: performance work",
        )

    def test_handles_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-4965",
                    "title": "performance work",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: performance work",
            },
        )

    def test_handles_status_change_value_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": "To Research",
                }
            },
            "issueId": "POI-4965",
            "title": "performance work",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: performance work",
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4965",
            "title": "performance work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4965"}
            )
        )


if __name__ == "__main__":
    unittest.main()
