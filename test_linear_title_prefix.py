import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4222",
                "title": "QA - Balance of plant does not appear",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4222",
                "title": "Cursor researching: QA - Balance of plant does not appear",
            },
        )

    def test_accepts_nested_linear_payload(self):
        update = build_issue_title_update(
            {
                "webhookType": "issue",
                "trigger": "statusChanged",
                "data": {
                    "id": "issue-id",
                    "title": "Investigate matching output",
                    "state": {"name": "to research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "issue-id")
        self.assertEqual(
            update["title"], "Cursor researching: Investigate matching output"
        )

    def test_accepts_status_fallback_when_new_status_missing(self):
        update = build_issue_title_update(
            {
                "trigger": "status changed",
                "issueId": "POI-4222",
                "status": "to_research",
                "title": "Review status automation",
            }
        )

        self.assertEqual(
            update["title"], "Cursor researching: Review status automation"
        )

    def test_ignores_non_status_change_triggers(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4222",
                "title": "Review status automation",
            }
        )

        self.assertIsNone(update)

    def test_ignores_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4222",
                "title": "Review status automation",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4222",
                "title": "cursor researching: Review status automation",
            }
        )

        self.assertIsNone(update)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Review status automation",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4222",
                    "title": "",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
