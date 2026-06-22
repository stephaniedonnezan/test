import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3259",
            "title": "design MVP",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3259",
                "title": "Cursor researching: design MVP",
            },
        )

    def test_prefixes_cloud_automation_trigger_context_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3259",
                    "title": "[]design MVP",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3259",
                "title": "Cursor researching: []design MVP",
            },
        )

    def test_accepts_status_changed_camel_case_and_to_research_camel_case(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate issue",
        )

    def test_prefixes_linear_update_when_updated_fields_include_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_prefers_changed_status_value_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Changed status",
                    "status": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status",
        )

    def test_accepts_updated_field_object_with_new_value(self):
        event = {
            "action": "updated",
            "updatedFields": [
                {"field": "state", "newValue": "to_research"},
            ],
            "identifier": "POI-4",
            "title": "Field object",
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4",
        )

    def test_accepts_updated_fields_mapping_with_status_value(self):
        event = {
            "action": "update",
            "updatedFields": {"workflowState": {"newValue": {"name": "To Research"}}},
            "key": "POI-5",
            "title": "Workflow mapping",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow mapping",
        )

    def test_ignores_non_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA UX/UI",
            "id": "POI-3259",
            "title": "design MVP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-3259",
            "title": "design MVP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-3259",
            "title": "design MVP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3259",
            "title": "cursor researching: design MVP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "design MVP",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3259",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
