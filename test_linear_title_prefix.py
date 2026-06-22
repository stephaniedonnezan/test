import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4171",
            "title": "Reduce transaction lifetime",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4171",
                "title": "Cursor researching: Reduce transaction lifetime",
            },
        )

    def test_builds_update_for_cloud_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4171",
                    "title": "Reduce transaction lifetime",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4171",
                "title": "Cursor researching: Reduce transaction lifetime",
            },
        )

    def test_normalizes_camel_case_trigger_and_status_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Investigate container load",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate container load",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-2",
            "title": "Ship it",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_explicit_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "A comment happened",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "cursor researching: Existing work",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_builds_update_for_generic_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Review flow",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Review flow",
            },
        )

    def test_builds_update_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "id": "webhook-event-id",
                "issue": {"identifier": "POI-6", "title": "Measure locking"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Measure locking",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-7",
            "title": "Rename only",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-8",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
