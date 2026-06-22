import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_builds_update_for_wrapped_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "TO_RESEARCH",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_builds_update_for_nested_linear_issue_status_change(self):
        event = {
            "webhookType": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "state": {"name": "ToResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_builds_update_for_generic_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "status": {"name": "To Research"},
            "issueId": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_prefers_explicit_change_status_over_current_status(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "status": "Done",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "cursor researching: MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
