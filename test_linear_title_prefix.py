import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_research_status_change(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4653",
                "title": "Share context between tabs",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4653",
                "title": "Cursor researching: Share context between tabs",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4653",
                "title": "Share context between tabs",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4653",
                "title": "Share context between tabs",
            }
        )

        self.assertIsNone(result)

    def test_skips_titles_that_already_have_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "id": "POI-4653",
                "title": "cursor researching: Share context between tabs",
            }
        )

        self.assertIsNone(result)

    def test_accepts_nested_trigger_context_payload(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4653",
                    "title": " Share context between tabs ",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4653",
                "title": "Cursor researching: Share context between tabs",
            },
        )

    def test_accepts_linear_issue_updated_payload_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-4653",
                        "title": "Share context between tabs",
                        "state": {"name": "to_research"},
                    }
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Share context between tabs")
        self.assertEqual(result["issueId"], "POI-4653")

    def test_webhook_type_does_not_mask_status_action(self):
        result = build_issue_title_update(
            {
                "webhookType": "issue",
                "action": "statusChanged",
                "status": "to-research",
                "issue": {
                    "id": "issue-id",
                    "title": "Share context between tabs",
                },
            }
        )

        self.assertEqual(result["issueId"], "issue-id")

    def test_requires_issue_id_and_title(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4653",
            }
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
