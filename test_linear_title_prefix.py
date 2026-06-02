import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4772",
            "title": "In the methane excel export, use 0 instead of N/A",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": (
                    "Cursor researching: "
                    "In the methane excel export, use 0 instead of N/A"
                ),
            },
        )

    def test_prefixes_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4772",
                "title": "In the methane excel export, use 0 instead of N/A",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": (
                    "Cursor researching: "
                    "In the methane excel export, use 0 instead of N/A"
                ),
            },
        )

    def test_prefixes_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4772",
                    "title": "Research mass-balance export",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": "Cursor researching: Research mass-balance export",
            },
        )

    def test_accepts_case_separator_and_camel_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4772",
            "title": "Normalize research status",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4772",
                "title": "Cursor researching: Normalize research status",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4772",
            "title": "In the methane excel export, use 0 instead of N/A",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4772",
            "title": "In the methane excel export, use 0 instead of N/A",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4772",
                "title": "Research mass-balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4772",
            "title": "cursor researching: Research mass-balance export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_or_incomplete_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4772",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
