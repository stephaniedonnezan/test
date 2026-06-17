import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4914",
                "title": "Button contained variants have shadows",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4914",
                "title": "Cursor researching: Button contained variants have shadows",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "To Research",
                "identifier": "POI-123",
                "title": "Investigate import mismatch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate import mismatch",
            },
        )

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS_CHANGED",
                "newStatus": "to_research",
                "issueId": "POI-456",
                "title": "Normalize webhook statuses",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize webhook statuses",
        )

    def test_prefixes_nested_linear_update_issue_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-789",
                    "title": "Review dashboard empty state",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review dashboard empty state",
            },
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4914",
                "title": "Button contained variants have shadows",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "dev",
                "id": "POI-4914",
                "title": "Button contained variants have shadows",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["description"],
                "issue": {
                    "identifier": "POI-321",
                    "title": "Refine issue copy",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4914",
                "title": "cursor researching: Button contained variants have shadows",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title_or_identifier(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "No issue id",
                    }
                }
            )
        )
        self.assertIsNone(build_issue_title_update({"triggerContext": "bad"}))


if __name__ == "__main__":
    unittest.main()
