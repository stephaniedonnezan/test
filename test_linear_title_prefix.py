import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4437",
            "title": "[5000]Show/download POS from mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4437",
                "title": "Cursor researching: [5000]Show/download POS from mass balance",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4437",
            "title": "Show/download POS from mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4437",
            "title": "Show/download POS from mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4437",
            "title": "cursor researching: Show/download POS from mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issue": {
                    "identifier": "POI-4437",
                    "title": "Show/download POS from mass balance",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4437",
                "title": "Cursor researching: Show/download POS from mass balance",
            },
        )

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["priority", "state"],
            "state": {"name": "To Research"},
            "issue": {
                "id": "issue-id",
                "title": "Clarify POS downloads",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Clarify POS downloads",
            },
        )

    def test_rejects_issue_updated_without_status_field(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "id": "POI-4437",
            "title": "Show/download POS from mass balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-4437",
            "title": "Show/download POS from mass balance",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Show/download POS from mass balance",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Show/download POS from mass balance",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4437",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
