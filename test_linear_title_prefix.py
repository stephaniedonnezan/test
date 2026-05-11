import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4352",
                "title": '[]"qualified input" page on the trader mass balance export',
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4352",
                "title": 'Cursor researching: []"qualified input" page on the trader mass balance export',
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4352",
            "title": "Qualified input page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4352",
            "title": "Qualified input page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4352",
            "title": "cursor researching: Qualified input page",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_issue_updated_with_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "status": "to-research",
            "issueId": "POI-4352",
            "title": "Qualified input page",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4352",
                "title": "Cursor researching: Qualified input page",
            },
        )

    def test_supports_nested_issue_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            },
            "data": {
                "issue": {
                    "identifier": "POI-4352",
                    "title": "Qualified input page",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4352",
                "title": "Cursor researching: Qualified input page",
            },
        )


if __name__ == "__main__":
    unittest.main()
