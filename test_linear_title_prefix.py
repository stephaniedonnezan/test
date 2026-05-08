import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4610",
                "title": "Potential bug - delivery ID 7991 ETD",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4610",
                "title": "Cursor researching: Potential bug - delivery ID 7991 ETD",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4610",
                "title": "Potential bug - delivery ID 7991 ETD",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4610",
                "title": "Potential bug - delivery ID 7991 ETD",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4610",
                "title": "cursor researching: Potential bug - delivery ID 7991 ETD",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4610",
                "title": "  Potential bug - delivery ID 7991 ETD  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4610",
                "title": "Cursor researching: Potential bug - delivery ID 7991 ETD",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "issueId": "POI-4610",
            "title": "Potential bug - delivery ID 7991 ETD",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4610",
                "title": "Cursor researching: Potential bug - delivery ID 7991 ETD",
            },
        )

    def test_reads_nested_issue_payload(self):
        event = {
            "type": "status_changed",
            "data": {
                "issue": {
                    "identifier": "POI-4610",
                    "title": "Potential bug - delivery ID 7991 ETD",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4610",
                "title": "Cursor researching: Potential bug - delivery ID 7991 ETD",
            },
        )

    def test_supports_issue_updated_when_status_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "id": "POI-4610",
                    "title": "Potential bug - delivery ID 7991 ETD",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4610",
                "title": "Cursor researching: Potential bug - delivery ID 7991 ETD",
            },
        )

    def test_ignores_issue_updated_without_status_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4610",
            "title": "Potential bug - delivery ID 7991 ETD",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Potential bug - delivery ID 7991 ETD",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4610",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
