import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3023",
            "title": "metric tonne to be used instead of ton",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3023",
                "title": "Cursor researching: metric tonne to be used instead of ton",
            },
        )

    def test_supports_cursor_cloud_wrapped_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3023",
                    "title": "metric tonne to be used instead of ton",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-3023")
        self.assertEqual(
            update["title"], "Cursor researching: metric tonne to be used instead of ton"
        )

    def test_supports_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3023",
                    "title": "metric tonne to be used instead of ton",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3023",
                "title": "Cursor researching: metric tonne to be used instead of ton",
            },
        )

    def test_accepts_separator_and_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-3023",
            "title": "metric tonne to be used instead of ton",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-3023",
            "title": "metric tonne to be used instead of ton",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3023",
            "title": "metric tonne to be used instead of ton",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_change_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "id": "POI-3023",
            "title": "metric tonne to be used instead of ton",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3023",
            "title": "cursor researching: metric tonne to be used instead of ton",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3023",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
