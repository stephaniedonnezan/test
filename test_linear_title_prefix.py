import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "To Research",
                    "id": "POI-4937",
                    "title": "Error: Unit kg is not supported for Electricity",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": (
                    "Cursor researching: "
                    "Error: Unit kg is not supported for Electricity"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "id": "POI-4937",
                "title": f"{TITLE_PREFIX}: Error: Unit kg is not supported for Electricity",
            }
        )

        self.assertIsNone(result)

    def test_matches_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issue_id": "POI-4937",
                "title": "Error: Unit kg is not supported for Electricity",
            }
        )

        self.assertEqual(
            result["title"],
            "Cursor researching: Error: Unit kg is not supported for Electricity",
        )

    def test_supports_nested_linear_issue_payload(self):
        result = build_issue_title_update(
            {
                "action": "statusChanged",
                "data": {
                    "issue": {
                        "id": "linear-issue-id",
                        "title": "Nested issue title",
                        "state": {"name": "to-research"},
                    }
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_supports_issue_updated_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": [{"name": "Workflow State"}],
                "status": "toResearch",
                "issueId": "POI-4937",
                "title": "Research this issue",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4937",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_ignores_issue_updated_without_status_field_changed(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description"],
                "status": "to research",
                "issueId": "POI-4937",
                "title": "Research this issue",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4937"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Title",
                }
            )
        )

    def test_handler_alias_uses_same_behavior(self):
        event = {
            "trigger": "stateChanged",
            "status": "to research",
            "identifier": "POI-4937",
            "title": "Alias support",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
