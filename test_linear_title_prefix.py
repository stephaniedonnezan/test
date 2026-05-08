import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_status_changed_to_research_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4444",
                "title": (
                    "Single POS issuance for trading sites - issue outgoing POS "
                    "from received batch"
                ),
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4444",
                "title": (
                    "Cursor researching: Single POS issuance for trading sites - "
                    "issue outgoing POS from received batch"
                ),
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4444",
                "title": "Single POS issuance for trading sites",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4444",
                "title": "Single POS issuance for trading sites",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4444",
                "title": "cursor researching: Single POS issuance for trading sites",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4444",
                "title": "cursor researching: Single POS issuance for trading sites",
            },
        )

    def test_accepts_case_and_separator_variants_for_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To_Research",
                "issueId": "POI-4444",
                "title": "Single POS issuance for trading sites",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Single POS issuance for trading sites",
        )

    def test_uses_nested_issue_data_with_outer_status_metadata(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "POI-4444",
                    "title": "Single POS issuance for trading sites",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4444",
                "title": "Cursor researching: Single POS issuance for trading sites",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["status"],
            "state": {"name": "To Research"},
            "identifier": "POI-4444",
            "title": "Single POS issuance for trading sites",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Single POS issuance for trading sites",
        )

    def test_ignores_issue_updated_without_status_field_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4444",
            "title": "Single POS issuance for trading sites",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_required_issue_data_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4444",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
