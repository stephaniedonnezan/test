import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4003",
            "title": "Display mass balance diagram for container site audits",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4003",
                "title": "Cursor researching: Display mass balance diagram for container site audits",
            },
        )

    def test_prefixes_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4003",
                    "title": "Display mass balance diagram for container site audits",
                    "status": "To Research",
                },
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4003")
        self.assertEqual(
            result["title"],
            "Cursor researching: Display mass balance diagram for container site audits",
        )

    def test_ignores_done_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4003",
            "title": "Display mass balance diagram for container site audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4003",
            "title": "Display mass balance diagram for container site audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4003",
            "title": "Cursor researching: Display mass balance diagram for container site audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4003",
            "title": "cursor researching: Display mass balance diagram for container site audits",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "identifier": "POI-4003",
            "title": "Display mass balance diagram for container site audits",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Display mass balance diagram for container site audits",
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4003",
                    "title": "Display mass balance diagram for container site audits",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4003",
                "title": "Cursor researching: Display mass balance diagram for container site audits",
            },
        )

    def test_accepts_new_status_from_changes_mapping(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"oldValue": "Todo", "newValue": "To Research"}},
            "issue": {
                "id": "issue-uuid",
                "title": "Display mass balance diagram for container site audits",
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "issue-uuid")

    def test_accepts_new_status_from_changes_list(self):
        event = {
            "action": "updated",
            "changes": [
                {"field": "workflowState", "from": "Todo", "to": {"name": "To Research"}},
            ],
            "issue": {
                "issueId": "POI-4003",
                "title": "Display mass balance diagram for container site audits",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Display mass balance diagram for container site audits",
        )

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4003",
                    "title": "Display mass balance diagram for container site audits",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4003",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
