import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Allow UBA POS creation for methane",
            },
        )

    def test_uses_nested_issue_data_from_linear_payloads(self):
        event = {
            "action": "statusChanged",
            "data": {
                "id": "linear-issue-id",
                "title": "Investigate certificate creation",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Investigate certificate creation",
            },
        )

    def test_flat_fields_override_nested_issue_data(self):
        event = {
            "trigger": "status changed",
            "new_status": "to research",
            "issueId": "POI-4198",
            "title": "Top level title",
            "data": {
                "id": "nested-id",
                "title": "Nested title",
                "state": {"name": "In Review"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Top level title",
            },
        )

    def test_accepts_identifier_when_id_is_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-4198",
            "title": "Research methane POS",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Research methane POS",
            },
        )

    def test_returns_none_for_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4198",
            "title": "Allow UBA POS creation for methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4198",
            "title": "Allow UBA POS creation for methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Allow UBA POS creation for methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4198",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4198",
            "title": "Cursor researching: Allow UBA POS creation for methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4198",
            "title": "cursor RESEARCHING - Allow UBA POS creation for methane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
