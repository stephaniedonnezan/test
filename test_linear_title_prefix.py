import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_changes_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_accepts_case_and_separator_variations_for_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: User removal flow",
        )

    def test_ignores_non_research_status_changes(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4974",
                "title": "cursor researching: User removal flow",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-4974",
                    "title": "User removal flow",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {
                "state": {
                    "oldValue": "Backlog",
                    "newValue": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_generic_update_requires_status_related_change(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4974",
                    "title": "User removal flow",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["title"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_linear_identifier_over_generic_envelope_id(self):
        event = {
            "id": "automation-envelope-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "identifier": "POI-4974",
                "title": "User removal flow",
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4974")

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4974 ",
                "title": " User removal flow ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4974",
                "title": "Cursor researching: User removal flow",
            },
        )

    def test_ignores_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
