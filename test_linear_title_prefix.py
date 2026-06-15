import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_prefixes_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4930",
                "title": "Optimize offtaker fifo allocation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
            "title": "cursor researching: Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4930",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Optimize offtaker fifo allocation",
        )

    def test_handles_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4930",
                    "title": "Optimize offtaker fifo allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4930",
                "title": "Cursor researching: Optimize offtaker fifo allocation",
            },
        )

    def test_ignores_generic_issue_updates_without_status_change_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4930",
                    "title": "Optimize offtaker fifo allocation",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_issue_identifier_is_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Optimize offtaker fifo allocation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_is_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4930",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
