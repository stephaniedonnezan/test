import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Create a demo for a methane site",
                "id": "POI-4612",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4612",
                "title": "Cursor researching: Create a demo for a methane site",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-1",
            "title": "Investigate issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate issue",
            },
        )

    def test_accepts_issue_update_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "status": "to-research",
            "issue": {
                "identifier": "POI-2",
                "title": "Nested event",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested event",
            },
        )

    def test_uses_nested_state_name_for_status(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-3",
            "title": "Nested state",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Nested state",
        )

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_issue_updated_requires_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "newStatus": "to research",
            "id": "POI-7",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-8",
                }
            )
        )

    def test_ignores_invalid_event(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
