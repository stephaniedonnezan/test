import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4788",
                "title": "Prevent inconsistent timelines for customer events at ingestion time",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4788",
                "title": (
                    "Cursor researching: Prevent inconsistent timelines for customer "
                    "events at ingestion time"
                ),
            },
        )

    def test_ignores_current_trigger_when_status_is_todo(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4788",
                "title": "Prevent inconsistent timelines for customer events at ingestion time",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4788",
                "title": "Prevent inconsistent timelines for customer events at ingestion time",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4788",
                "title": (
                    "cursor researching: Prevent inconsistent timelines for customer "
                    "events at ingestion time"
                ),
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "statusChanged",
                        "newStatus": status,
                        "id": "POI-4788",
                        "title": "Prevent inconsistent timelines",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Prevent inconsistent timelines",
                )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4788",
                    "title": "Prevent inconsistent timelines",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4788",
                "title": "Cursor researching: Prevent inconsistent timelines",
            },
        )

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4788",
                    "title": "Prevent inconsistent timelines",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": " POI-4788 ",
                "title": " Prevent inconsistent timelines ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4788",
                "title": "Cursor researching: Prevent inconsistent timelines",
            },
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
