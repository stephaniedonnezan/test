import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_title_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-3655",
                "title": "Improve the Visual Appearance of Alerts",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3655",
                "title": "Cursor researching: Improve the Visual Appearance of Alerts",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-3655",
                "title": "Improve the Visual Appearance of Alerts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3655",
                "title": "Improve the Visual Appearance of Alerts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_research_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-3655",
            "title": "cursor researching: Improve the Visual Appearance of Alerts",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Nested issue title",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_supports_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": [{"name": "Workflow State"}],
            "status": "toResearch",
            "issueId": "POI-3655",
            "title": "Research this issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3655",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_ignores_issue_updated_without_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-3655",
            "title": "Research this issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to research",
            "identifier": "POI-3655",
            "title": "Alias support",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
