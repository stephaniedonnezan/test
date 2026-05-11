import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4623",
                "title": "ensure storage losses are reported",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4623",
                "title": "Cursor researching: ensure storage losses are reported",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Duplicate",
            "id": "POI-4623",
            "title": "ensure storage losses are reported",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4623",
            "title": "ensure storage losses are reported",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4623",
            "title": "cursor researching: ensure storage losses are reported",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_casing_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-4623",
            "title": "ensure storage losses are reported",
        }

        result = build_issue_title_update(event)

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4623",
                "title": "Cursor researching: ensure storage losses are reported",
            },
        )

    def test_accepts_linear_issue_updated_status_field_payloads(self):
        event = {
            "webhookType": "issue",
            "updatedFields": ["status"],
            "state": {"name": "To Research"},
            "identifier": "POI-4623",
            "title": "ensure storage losses are reported",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4623",
                "title": "Cursor researching: ensure storage losses are reported",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4623"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "ensure storage losses are reported",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
