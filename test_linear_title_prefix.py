import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4533",
            "title": "Investigate Shell HH1 Trading error",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4533",
                "title": "Cursor researching: Investigate Shell HH1 Trading error",
            },
        )

    def test_accepts_nested_linear_payload(self):
        event = {
            "type": "Issue",
            "action": "statusChanged",
            "data": {
                "id": "issue-123",
                "title": "Reconcile January close",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Reconcile January close",
            },
        )

    def test_falls_back_to_status_when_new_status_missing(self):
        event = {
            "trigger": "status changed",
            "status": "to_research",
            "issueId": "POI-4533",
            "title": "Research missing report",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research missing report",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4533",
            "title": "Investigate issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4533",
            "title": "Investigate issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4533",
            "title": "cursor researching: Investigate issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Investigate issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4533",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
