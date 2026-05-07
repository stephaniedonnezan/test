import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4650",
                "title": "All Container events are about 700kg",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: All Container events are about 700kg",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4650",
                "title": "All Container events are about 700kg",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_trigger_types(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4650",
                "title": "All Container events are about 700kg",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4650",
                "title": "cursor researching: All Container events are about 700kg",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4650",
            "title": "Container MB shows split mass",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: Container MB shows split mass",
            },
        )

    def test_normalizes_status_separators(self):
        event = {
            "trigger": "status changed",
            "new_status": "to-research",
            "id": "POI-4650",
            "title": "Container MB shows split mass",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: Container MB shows split mass",
            },
        )

    def test_reads_nested_issue_payload(self):
        event = {
            "triggerContext": {"trigger": "status_changed", "newStatus": "to research"},
            "data": {
                "issue": {
                    "identifier": "POI-4650",
                    "title": "Container MB shows split mass",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: Container MB shows split mass",
            },
        )

    def test_uses_state_name_status_fallback(self):
        event = {
            "action": "status_changed",
            "state": {"name": "To Research"},
            "id": "POI-4650",
            "title": "Container MB shows split mass",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: Container MB shows split mass",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": " POI-4650 ",
            "title": " Container MB shows split mass ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4650",
                "title": "Cursor researching: Container MB shows split mass",
            },
        )

    def test_ignores_missing_issue_details(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research"}
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
