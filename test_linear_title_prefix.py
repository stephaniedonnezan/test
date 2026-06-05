import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4844",
                "title": "A - UI formatters render in the site's timezone",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4844",
                "title": "Cursor researching: A - UI formatters render in the site's timezone",
            },
        )

    def test_normalizes_camel_case_status_changed_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4844",
                "title": "UI formatters render in the site's timezone",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-4844")
        self.assertEqual(
            update["title"],
            "Cursor researching: UI formatters render in the site's timezone",
        )

    def test_ignores_current_todo_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4844",
                "title": "A - UI formatters render in the site's timezone",
                "status": "Todo",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4844",
                "title": "A - UI formatters render in the site's timezone",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_when_changed_fields_do_not_include_status(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-4844",
                    "title": "A - UI formatters render in the site's timezone",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_with_changes(self):
        event = {
            "action": "update",
            "data": {
                "changes": {
                    "state": {
                        "from": {"name": "Todo"},
                        "to": {"name": "To Research"},
                    }
                },
                "issue": {
                    "identifier": "POI-4844",
                    "title": "A - UI formatters render in the site's timezone",
                    "state": {"name": "Todo"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4844",
                "title": "Cursor researching: A - UI formatters render in the site's timezone",
            },
        )

    def test_supports_nested_linear_update_with_updated_fields(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "updatedFields": [{"field": "workflowState"}],
                "issue": {
                    "id": "issue-123",
                    "identifier": "POI-4844",
                    "title": "A - UI formatters render in the site's timezone",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: A - UI formatters render in the site's timezone",
            },
        )

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4844",
                "title": "cursor researching: A - UI formatters render in the site's timezone",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4844",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "A - UI formatters render in the site's timezone",
                    }
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
