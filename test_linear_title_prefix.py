import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3310",
                "title": "Create different supply chain types",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3310",
                "title": "Cursor researching: Create different supply chain types",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-3310",
                "title": "Create different supply chain types",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3310",
                "title": "Create different supply chain types",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3310",
                "title": "cursor researching: Create different supply chain types",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_trigger_and_status_names(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-3310",
                "title": "Create different supply chain types",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Create different supply chain types",
        )

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3310",
                    "title": "Create different supply chain types",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3310",
                "title": "Cursor researching: Create different supply chain types",
            },
        )

    def test_handles_changed_status_values(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"newValue": {"name": "to research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-3310",
                    "title": "Create different supply chain types",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-3310",
        )

    def test_ignores_missing_issue_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3310",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
