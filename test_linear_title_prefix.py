import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4565",
                "title": "Clear node filter on month switch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4565",
                "title": "Cursor researching: Clear node filter on month switch",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4565",
            "title": "Clear node filter on month switch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4565",
            "title": "Clear node filter on month switch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4565",
            "title": "cursor researching: Clear node filter on month switch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "action": "statusChanged",
            "status": "To_Research",
            "issueId": "POI-4565",
            "title": "Clear node filter on month switch",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4565",
                "title": "Cursor researching: Clear node filter on month switch",
            },
        )

    def test_accepts_linear_data_issue_payload_shape(self):
        event = {
            "type": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4565",
                    "title": "Clear node filter on month switch",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4565",
                "title": "Cursor researching: Clear node filter on month switch",
            },
        )

    def test_uses_outer_automation_metadata_with_nested_issue(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "lin-123",
                    "title": "Clear node filter on month switch",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "lin-123",
                "title": "Cursor researching: Clear node filter on month switch",
            },
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status changed",
            "new_status": "to-research",
            "id": "POI-4565",
            "title": "  Clear node filter on month switch  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4565",
                "title": "Cursor researching: Clear node filter on month switch",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Clear node filter on month switch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4565",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
