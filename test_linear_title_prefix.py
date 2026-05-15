import unittest

from linear_title_prefix import (
    RESEARCH_TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3763",
                "title": "Update the deliveries download template",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3763",
                "title": "Cursor researching: Update the deliveries download template",
            },
        )

    def test_builds_update_for_linear_issue_webhook_payload(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "title": "Research title automation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research title automation",
            },
        )

    def test_treats_status_case_punctuation_and_spacing_as_equivalent(self):
        event = {
            "webhookType": "issue",
            "trigger": "state-changed",
            "new_status": "  To-Research  ",
            "issue_id": "POI-1",
            "title": "Trimmed title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_uses_nested_issue_data_when_present(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_compatibility_wrapper_delegates_to_builder(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Wrapper issue",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4",
            "title": "Ready for QA",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_updates(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-5",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": f"{RESEARCH_TITLE_PREFIX}: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))


if __name__ == "__main__":
    unittest.main()
