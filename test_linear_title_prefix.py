import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_automation_trigger_adds_research_prefix(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4159",
                    "title": "Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4159",
                "title": "Cursor researching: Deliveries xls upload is not blocked",
            },
        )

    def test_ignores_other_new_status(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Todo",
                    "id": "POI-4159",
                    "title": "Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_change_trigger(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-4159",
                    "title": "Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertIsNone(action)

    def test_avoids_duplicate_prefix_case_insensitively(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4159",
                    "title": "cursor researching: Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertIsNone(action)

    def test_normalizes_status_and_trigger_casing(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "new_status": "To_Research",
                    "issueId": "POI-4159",
                    "title": "Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Deliveries xls upload is not blocked")

    def test_reads_nested_linear_issue_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "issue-uuid",
                        "title": "Deliveries xls upload is not blocked",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(action["issueId"], "issue-uuid")
        self.assertEqual(action["title"], "Cursor researching: Deliveries xls upload is not blocked")

    def test_reads_updated_from_state_id_as_status_change(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFrom": {"stateId": "previous-state"},
                "data": {
                    "id": "issue-uuid",
                    "title": "Deliveries xls upload is not blocked",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(action["issueId"], "issue-uuid")

    def test_ignores_issue_update_without_status_field_change(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["title"],
                "data": {
                    "id": "issue-uuid",
                    "title": "Deliveries xls upload is not blocked",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(action)

    def test_accepts_identifier_when_id_is_absent(self):
        action = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "identifier": "POI-4159",
                    "title": "Deliveries xls upload is not blocked",
                }
            }
        )

        self.assertEqual(action["issueId"], "POI-4159")

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))


if __name__ == "__main__":
    unittest.main()
