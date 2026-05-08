import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2835",
                "title": "[5000]Prevent meter readings being edited",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2835",
                "title": "Cursor researching: [5000]Prevent meter readings being edited",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-2835",
                "title": "Prevent meter readings being edited",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2835",
                "title": "Prevent meter readings being edited",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2835",
                "title": "cursor researching: Prevent meter readings being edited",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issue_id": "POI-2835",
                "title": "Prevent meter readings being edited",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2835",
                "title": "Cursor researching: Prevent meter readings being edited",
            },
        )

    def test_supports_issue_updated_payloads_when_status_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "data": {
                "id": "POI-2835",
                "title": "Prevent meter readings being edited",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2835",
                "title": "Cursor researching: Prevent meter readings being edited",
            },
        )

    def test_supports_nested_issue_fields(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "identifier": "POI-2835",
                    "title": "Prevent meter readings being edited",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2835",
                "title": "Cursor researching: Prevent meter readings being edited",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2835",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
