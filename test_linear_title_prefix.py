import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_title_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4677",
                "title": "Removal of RFNBO character on batches",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4677",
                "title": "Cursor researching: Removal of RFNBO character on batches",
            },
        )

    def test_ignores_status_changed_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4677",
                "title": "Removal of RFNBO character on batches",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4677",
                "title": "Removal of RFNBO character on batches",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_researching_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4677",
            "title": "cursor researching: Removal of RFNBO character on batches",
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
            "issueId": "POI-4677",
            "title": "Research this issue",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4677",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_ignores_issue_updated_without_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-4677",
            "title": "Research this issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "new_status": "to research",
            "identifier": "POI-4677",
            "title": "Alias support",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
