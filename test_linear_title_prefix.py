import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_payload_when_status_changes_to_research(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5036",
                "title": "Mass Balance canvas items in delivery opacity off",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5036",
                "title": "Cursor researching: Mass Balance canvas items in delivery opacity off",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5036",
                "title": "Mass Balance canvas items in delivery opacity off",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5036",
                "title": "Mass Balance canvas items in delivery opacity off",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5036",
                "title": "cursor researching: Mass Balance canvas items in delivery opacity off",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-5036",
                "title": "Mass Balance canvas items in delivery opacity off",
            }
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Cursor researching: Mass Balance canvas items in delivery opacity off")

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5036",
                    "title": "Mass Balance canvas items in delivery opacity off",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5036",
                "title": "Cursor researching: Mass Balance canvas items in delivery opacity off",
            },
        )

    def test_handles_status_change_value_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5036",
                    "title": "Mass Balance canvas items in delivery opacity off",
                }
            },
        }

        result = build_issue_title_update(event)

        self.assertIsNotNone(result)
        self.assertEqual(result["issueId"], "POI-5036")

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5036",
                    "title": "Mass Balance canvas items in delivery opacity off",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
