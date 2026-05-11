import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4665",
                "title": "Make a unit test that checks every field",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4665",
                "title": (
                    "Cursor researching: "
                    "Make a unit test that checks every field"
                ),
            },
        )

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-4665",
            "title": "Research title automation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research title automation",
        )

    def test_reads_issue_data_from_nested_linear_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4665",
                    "title": "Nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4665",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_supports_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "status": "to_research",
            "id": "POI-4665",
            "title": "Updated issue payload",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Updated issue payload",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4665",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4665",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updated_without_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4665",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4665",
            "title": "cursor researching: Existing title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing title",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4665",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
