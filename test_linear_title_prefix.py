import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3995",
                "title": "Storage losses should also be added to credit output",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3995",
                "title": (
                    "Cursor researching: "
                    "Storage losses should also be added to credit output"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-3995",
                "title": "Storage losses should also be added to credit output",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3995",
                "title": "Storage losses should also be added to credit output",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "id": "POI-3995",
            "title": "cursor researching: Storage losses",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-3995",
            "title": "Storage losses",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3995",
                "title": "Cursor researching: Storage losses",
            },
        )

    def test_uses_webhook_issue_shape(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3995",
                    "title": "Storage losses",
                },
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3995",
                "title": "Cursor researching: Storage losses",
            },
        )

    def test_uses_issue_id_when_state_has_its_own_id(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Storage losses",
                },
                "state": {"id": "state-id", "name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Storage losses",
            },
        )

    def test_accepts_status_objects(self):
        event = {
            "trigger": "status_changed",
            "status": {"name": "To Research"},
            "id": "POI-3995",
            "title": "Storage losses",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3995",
                "title": "Cursor researching: Storage losses",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Storage losses",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3995",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
