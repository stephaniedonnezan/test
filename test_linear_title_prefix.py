import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        action = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4522",
                    "title": "Cross border PPA",
                    "status": "Todo",
                },
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4522",
                "title": "Cursor researching: Cross border PPA",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-1",
                "title": "Investigate import flow",
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Investigate import flow")

    def test_prefixes_nested_linear_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-2",
                        "title": "Nested payload",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-2")
        self.assertEqual(action["title"], "Cursor researching: Nested payload")

    def test_explicit_new_status_beats_stale_nested_status(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newState": "To Research",
                    "data": {
                        "issue": {
                            "id": "POI-3",
                            "title": "Stale state",
                            "state": {"name": "Todo"},
                        }
                    },
                }
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Stale state")

    def test_ignores_non_research_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4",
                "title": "Wrong status",
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_change_events(self):
        action = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5",
                "title": "Wrong trigger",
            }
        )

        self.assertIsNone(action)

    def test_ignores_update_without_status_field_change(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "newStatus": "To Research",
                "id": "POI-6",
                "title": "Title-only update",
            }
        )

        self.assertIsNone(action)

    def test_avoids_duplicate_prefix_case_insensitively(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": "cursor researching: Already marked",
            }
        )

        self.assertIsNone(action)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-8",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
