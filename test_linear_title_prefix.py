import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed with code 412",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with code 412",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4644",
                "title": "GET /automate/sites failed with code 412",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed with code 412",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4644",
                "title": "cursor researching: GET /automate/sites failed with code 412",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4644",
                "title": "GET /automate/sites failed with code 412",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with code 412",
            },
        )

    def test_handles_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "POI-4644",
                    "title": "GET /automate/sites failed with code 412",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with code 412",
            },
        )

    def test_generic_update_must_include_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["assignee"],
            "data": {
                "issue": {
                    "id": "POI-4644",
                    "title": "GET /automate/sites failed with code 412",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issueId": "POI-4644",
            "title": "GET /automate/sites failed with code 412",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed with code 412",
            },
        )


if __name__ == "__main__":
    unittest.main()
