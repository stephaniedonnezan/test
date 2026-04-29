import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4583",
            "title": "Issue with Export XLS button",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Issue with Export XLS button",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4583",
                "title": "Container events export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Container events export",
            },
        )

    def test_accepts_nested_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "newStatus": "to_research",
                "issue": {
                    "id": "issue-123",
                    "title": "Search export containers",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-123",
                "title": "Cursor researching: Search export containers",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_data(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "outer-id",
            "title": "Outer title",
            "issue": {
                "id": "nested-id",
                "title": "Nested title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "outer-id",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_falls_back_to_state_name_for_status(self):
        event = {
            "webhookType": "status_changed",
            "state": {"name": "To Research"},
            "issueId": "POI-4583",
            "title": "Use state name",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Use state name",
            },
        )

    def test_accepts_issue_id_alias(self):
        event = {
            "type": "statusChanged",
            "status": "to-research",
            "issue_id": "POI-4583",
            "title": "Issue id alias",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Issue id alias",
            },
        )

    def test_accepts_identifier_as_issue_id_alias(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-4583",
            "title": "Identifier alias",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Identifier alias",
            },
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4583",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4583",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4583",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4583",
            "title": "Container events export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4583",
            "title": "Container events export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_non_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4583",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["status_changed"]))


if __name__ == "__main__":
    unittest.main()
