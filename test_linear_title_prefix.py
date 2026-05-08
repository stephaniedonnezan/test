import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4461",
                "title": "Build frontend flow for locking production site outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4461",
                "title": "Cursor researching: Build frontend flow for locking production site outputs",
            },
        )

    def test_ignores_non_research_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4461",
            "title": "Build frontend flow for locking production site outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4461",
            "title": "Build frontend flow for locking production site outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "id": "POI-4461",
            "title": "cursor researching: Build frontend flow for locking production site outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "issueId": "POI-4461",
                    "title": "Build frontend flow for locking production site outputs",
                    "state": {"name": "ToResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4461",
                "title": "Cursor researching: Build frontend flow for locking production site outputs",
            },
        )

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4461",
            "title": "Build frontend flow for locking production site outputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_kebab_case_status_and_identifier(self):
        event = {
            "type": "state-change",
            "new_status": "to-research",
            "identifier": "POI-4461",
            "title": "Build frontend flow for locking production site outputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4461",
                "title": "Cursor researching: Build frontend flow for locking production site outputs",
            },
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))


if __name__ == "__main__":
    unittest.main()
