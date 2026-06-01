import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4778",
            "title": "Sub issue of MB export revamp",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4778",
                "title": "Cursor researching: Sub issue of MB export revamp",
            },
        )

    def test_accepts_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4778",
                "title": "Sub issue of MB export revamp",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4778",
                "title": "Cursor researching: Sub issue of MB export revamp",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4778",
                "title": "Sub issue of MB export revamp",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4778",
                "title": "Cursor researching: Sub issue of MB export revamp",
            },
        )

    def test_normalizes_status_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4778",
            "title": "Sub issue of MB export revamp",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4778",
            "title": "Sub issue of MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4778",
            "title": "Sub issue of MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4778",
                "title": "Sub issue of MB export revamp",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4778",
            "title": "cursor researching: Sub issue of MB export revamp",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))


if __name__ == "__main__":
    unittest.main()
