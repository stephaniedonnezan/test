import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4644",
                "title": "cursor researching: GET /automate/sites failed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_supports_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "issueId": "POI-4644",
            "title": "GET /automate/sites failed",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_supports_linear_data_issue_payloads(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4644",
                    "title": "GET /automate/sites failed",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_supports_issue_updated_with_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "new_status": "to-research",
            "issue": {
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_ignores_issue_updated_without_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "issue": {
                "id": "POI-4644",
                "title": "GET /automate/sites failed",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4644 ",
                "title": "  GET /automate/sites failed  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4644",
                "title": "Cursor researching: GET /automate/sites failed",
            },
        )

    def test_ignores_missing_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4644",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
