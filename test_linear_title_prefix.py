import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5077",
                "title": "Investigate meter warning",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5077",
                "title": "Cursor researching: Investigate meter warning",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-5077",
                "title": "QA report - POI-4878 LPH without BOP",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5077",
                "title": "Investigate meter warning",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "identifier": "POI-5077",
                "title": "cursor researching: Investigate meter warning",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5077",
                "title": "cursor researching: Investigate meter warning",
            },
        )

    def test_matches_status_and_trigger_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "StatusChanged",
                "new_status": "TO_RESEARCH",
                "issueId": "POI-5077",
                "title": "Investigate meter warning",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate meter warning",
        )

    def test_handles_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5077",
                    "title": "Investigate meter warning",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5077",
                "title": "Cursor researching: Investigate meter warning",
            },
        )

    def test_handles_nested_changes_with_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"old": "Todo", "new": "to research"}},
            "data": {
                "issue": {
                    "key": "POI-5077",
                    "title": "Investigate meter warning",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5077",
        )

    def test_ignores_generic_updates_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5077",
                    "title": "Investigate meter warning",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_nested_issue_fields_over_wrapper_metadata(self):
        event = {
            "id": "webhook-event-id",
            "title": "Webhook event title",
            "action": "update",
            "changes": {"workflowState": {"to": {"name": "to research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5077",
                    "title": "Investigate meter warning",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5077",
                "title": "Cursor researching: Investigate meter warning",
            },
        )

    def test_ignores_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate meter warning",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5077",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
