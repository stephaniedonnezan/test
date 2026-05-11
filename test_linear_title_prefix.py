import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4536",
                "title": "Incorrect mass balance error",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4536",
                "title": "Cursor researching: Incorrect mass balance error",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4536",
                "title": "Incorrect mass balance error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4536",
                "title": "Incorrect mass balance error",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-4536",
            "title": "cursor researching: Incorrect mass balance error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_matches_status_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-4536",
            "title": "Incorrect mass balance error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4536",
                "title": "Cursor researching: Incorrect mass balance error",
            },
        )

    def test_accepts_nested_linear_data_issue_shape(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4536",
                    "title": "Incorrect mass balance error",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4536",
                "title": "Cursor researching: Incorrect mass balance error",
            },
        )

    def test_issue_updated_requires_status_related_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4536",
            "title": "Incorrect mass balance error",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_top_level_automation_fields_over_nested_issue_fields(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "issue": {
                    "id": "nested-id",
                    "title": "Nested title",
                    "status": "to research",
                },
            },
            "newStatus": "to research",
            "id": "POI-4536",
            "title": "Incorrect mass balance error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4536",
                "title": "Cursor researching: Incorrect mass balance error",
            },
        )

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4536 ",
            "title": "  Incorrect mass balance error  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4536",
                "title": "Cursor researching: Incorrect mass balance error",
            },
        )

    def test_ignores_missing_required_fields(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research"}
            )
        )
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
