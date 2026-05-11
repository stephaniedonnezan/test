import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4575",
                "title": "Mass balance export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4575",
                "title": "Cursor researching: Mass balance export",
            },
        )

    def test_accepts_flat_payload_and_status_fallback(self):
        event = {
            "trigger": "status_changed",
            "status": "  to   research  ",
            "issueId": "POI-123",
            "title": "Investigate feedstock import",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate feedstock import",
            },
        )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-456",
                "title": "cursor researching: Existing work",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "cursor researching: Existing work",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4575",
                "title": "Mass balance export",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4575",
                "title": "Mass balance export",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({"triggerContext": []}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4575",
                    "title": " ",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
