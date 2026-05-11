import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_automation_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4451",
                "title": "Investigate final allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4451",
                "title": "Cursor researching: Investigate final allocation",
            },
        )

    def test_ignores_other_new_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4451",
                "title": "Investigate final allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4451",
                "title": "Investigate final allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4451",
                "title": "cursor researching: Investigate final allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-4451",
                "title": "Investigate final allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4451",
                "title": "Cursor researching: Investigate final allocation",
            },
        )

    def test_supports_linear_issue_update_payloads_with_changed_status(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "identifier": "POI-4451",
                "title": "Investigate final allocation",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4451",
                "title": "Cursor researching: Investigate final allocation",
            },
        )

    def test_supports_nested_issue_payloads(self):
        event = {
            "webhookType": "Issue Updated",
            "updated_fields": {"state": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "POI-4451",
                    "title": "Investigate final allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4451",
                "title": "Cursor researching: Investigate final allocation",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4451",
                    }
                }
            )
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a dict"))


if __name__ == "__main__":
    unittest.main()
