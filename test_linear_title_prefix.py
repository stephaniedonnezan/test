import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_for_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4762",
                "title": "UBA PoS PDF",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4762",
                "title": "Cursor researching: UBA PoS PDF",
            },
        )

    def test_ignores_status_changed_event_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4762",
                "title": "UBA PoS PDF",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_event(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4762",
                "title": "UBA PoS PDF",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4762",
                "title": "Cursor researching: UBA PoS PDF",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "id": "POI-4762",
                "title": "cursor researching - UBA PoS PDF",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": {
                    "state": {
                        "from": {"name": "Todo"},
                        "to": {"name": "To Research"},
                    }
                },
                "issue": {
                    "id": "POI-4762",
                    "title": "UBA PoS PDF",
                    "state": {"name": "Todo"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4762",
                "title": "Cursor researching: UBA PoS PDF",
            },
        )

    def test_ignores_update_without_status_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": {"title": {"from": "Old", "to": "New"}},
                "issue": {
                    "id": "POI-4762",
                    "title": "UBA PoS PDF",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_updated_fields_list_payload(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "updatedFields": [
                    {
                        "field": "workflowState",
                        "to": {"name": "to-research"},
                    }
                ],
                "issue": {
                    "identifier": "POI-4762",
                    "title": "UBA PoS PDF",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4762",
                "title": "Cursor researching: UBA PoS PDF",
            },
        )

    def test_uses_status_fallback_when_new_status_is_not_separate(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4762",
                "title": "UBA PoS PDF",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4762",
                "title": "Cursor researching: UBA PoS PDF",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "UBA PoS PDF",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
