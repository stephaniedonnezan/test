import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4554",
                "title": "Bug: reopening a mass balance produces duplicates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4554",
                "title": "Cursor researching: Bug: reopening a mass balance produces duplicates",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4554",
                "title": "Bug: reopening a mass balance produces duplicates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_when_status_matches(self):
        event = {
            "triggerContext": {
                "trigger": "label_changed",
                "newStatus": "to research",
                "id": "POI-4554",
                "title": "Bug: reopening a mass balance produces duplicates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4554",
                "title": "cursor researching: Bug: reopening a mass balance produces duplicates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_research_status_separators_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS_CHANGED",
                "newStatus": "To-Research",
                "issueId": "POI-4554",
                "title": "  Bug: reopening a mass balance produces duplicates  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4554",
                "title": "Cursor researching: Bug: reopening a mass balance produces duplicates",
            },
        )

    def test_supports_nested_linear_issue_update_with_state_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4554",
                    "title": "Bug: reopening a mass balance produces duplicates",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4554",
                "title": "Cursor researching: Bug: reopening a mass balance produces duplicates",
            },
        )

    def test_supports_linear_updated_from_state_id_marker(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "identifier": "POI-4554",
                "title": "Bug: reopening a mass balance produces duplicates",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4554",
                "title": "Cursor researching: Bug: reopening a mass balance produces duplicates",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4554",
                "title": "Bug: reopening a mass balance produces duplicates",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-4554"})
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
