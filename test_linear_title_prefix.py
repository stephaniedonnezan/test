import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4573",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4573",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4573",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4573",
                "title": "Random stock overflow on Turn2X Jan 2026",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_accepts_nested_issue_data_payload(self):
        event = {
            "trigger": "statusChanged",
            "data": {
                "issue": {
                    "issueId": "POI-4573",
                    "title": "Random stock overflow on Turn2X Jan 2026",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "status"],
            "status": "to-research",
            "identifier": "POI-4573",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4573",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4573",
            "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4573",
            "title": "cursor researching - Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Random stock overflow on Turn2X Jan 2026",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4573",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
