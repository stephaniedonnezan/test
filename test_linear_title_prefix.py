import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1629",
                "title": "New Graph for Temporal Correlation Graph",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1629",
                "title": "Cursor researching: New Graph for Temporal Correlation Graph",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-1629",
                "title": "New Graph for Temporal Correlation Graph",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-1629",
                "title": "New Graph for Temporal Correlation Graph",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-1629",
                "title": "cursor researching: New Graph for Temporal Correlation Graph",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_case_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-1629",
                "title": "New Graph for Temporal Correlation Graph",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1629",
                "title": "Cursor researching: New Graph for Temporal Correlation Graph",
            },
        )

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-1629",
                    "title": "New Graph for Temporal Correlation Graph",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1629",
                "title": "Cursor researching: New Graph for Temporal Correlation Graph",
            },
        )

    def test_uses_changed_status_value_from_linear_changes(self):
        event = {
            "action": "update",
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-1629",
                    "title": "New Graph for Temporal Correlation Graph",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1629",
                "title": "Cursor researching: New Graph for Temporal Correlation Graph",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-1629",
                    "title": "New Graph for Temporal Correlation Graph",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
