import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_linear_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3974",
                "title": "POSes are wrong",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3974",
                "title": "Cursor researching: POSes are wrong",
            },
        )

    def test_prefixes_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "title": "Investigate container preview",
                "state": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate container preview",
            },
        )

    def test_accepts_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-1",
            "title": "Handle compact payloads",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Handle compact payloads",
            },
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-2",
            "title": "Leave comments alone",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3",
            "title": "Already finished",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-5",
                "title": "Only the title changed",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
