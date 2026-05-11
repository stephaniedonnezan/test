import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2586",
                "title": "[250]UX- Make preview consistent",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2586",
                "title": "Cursor researching: [250]UX- Make preview consistent",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Research document actions",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research document actions",
            },
        )

    def test_accepts_issue_updated_when_status_changed(self):
        event = {
            "webhookType": "Issue Updated",
            "updatedFields": ["description", "status"],
            "new_status": "to-research",
            "issueId": "POI-124",
            "title": "Validate research handoff",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Validate research handoff",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-2586",
            "title": "Completed issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_issue_update(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-2586",
            "title": "Title-only edit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2586",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-2586",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
