import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4973",
                "title": "Roles in the invite flow includes auditor",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4973",
                "title": "Cursor researching: Roles in the invite flow includes auditor",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-4973",
                "title": "Research target status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4973",
                "title": "Cursor researching: Research target status",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4973",
                "title": "Roles in the invite flow includes auditor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4973",
                "title": "Roles in the invite flow includes auditor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_marker(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4973",
                "title": "cursor researching: Roles in the invite flow includes auditor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefixes_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4973",
                    "title": "Nested Linear payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4973",
                "title": "Cursor researching: Nested Linear payload",
            },
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4973",
                    "title": "Description-only update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_changes_object_new_state(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4973",
                    "title": "Changes object payload",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4973",
                "title": "Cursor researching: Changes object payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
