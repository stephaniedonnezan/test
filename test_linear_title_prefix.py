import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4473",
                "title": "Review if we need to migrate co2 qualifed inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4473",
                "title": "Cursor researching: Review if we need to migrate co2 qualifed inputs",
            },
        )

    def test_accepts_nested_linear_webhook_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "id": "POI-123",
                    "title": "Scope hydrogen certificate copy",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Scope hydrogen certificate copy",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["assignee", "workflowState"],
            "issueId": "POI-456",
            "title": "Decide biomethane defaults",
            "workflowState": {"name": "to-research"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Decide biomethane defaults",
            },
        )

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "issueId": "POI-456",
            "title": "Decide biomethane defaults",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-789",
            "title": "Investigate ledger export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4473",
            "title": "Review if we need to migrate co2 qualifed inputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-999",
            "title": "cursor researching: Check feedstock mapping",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": "toResearch",
            "identifier": " POI-100 ",
            "title": "  Research registry import  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Research registry import",
            },
        )

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-111",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
