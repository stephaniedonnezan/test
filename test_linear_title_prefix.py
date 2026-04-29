import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4509",
                "title": "Cursor researching: Org user can edit audit dates",
            },
        )

    def test_supports_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4509",
            "title": "Org user can edit audit dates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4509",
                "title": "Cursor researching: Org user can edit audit dates",
            },
        )

    def test_accepts_separator_variants_for_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "to_research",
                "issueId": "POI-4509",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Org user can edit audit dates",
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4509",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Org user can edit audit dates",
        )

    def test_does_not_update_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4509",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": "Cursor researching: Org user can edit audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": "cursor researching - Org user can edit audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": "  Org user can edit audit dates  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Org user can edit audit dates",
        )

    def test_requires_issue_identifier(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Org user can edit audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4509",
                "title": " ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
