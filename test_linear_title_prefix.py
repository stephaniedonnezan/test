import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_status_changed_to_research_payload(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3756",
                "title": 'QueryFailedError: update or delete on table "delivery"',
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3756",
                "title": 'Cursor researching: QueryFailedError: update or delete on table "delivery"',
            },
        )

    def test_accepts_cloud_automation_trigger_context_wrapper(self):
        result = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "trigger": "statusChanged",
                        "newStatus": "to_research",
                        "id": "POI-100",
                        "title": "Investigate webhook payload",
                    }
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Investigate webhook payload",
            },
        )

    def test_accepts_nested_linear_issue_update_when_state_changed(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-101",
                        "title": "Research nested payload",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Research nested payload",
            },
        )

    def test_accepts_generic_issue_updated_payload_with_workflow_state_changes(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
                "data": {
                    "identifier": "POI-102",
                    "title": "Research workflow state payload",
                    "workflowState": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-102",
                "title": "Cursor researching: Research workflow state payload",
            },
        )

    def test_uses_status_field_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "status": "to-research",
                "issueId": "POI-103",
                "title": "Research status fallback",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-103",
                "title": "Cursor researching: Research status fallback",
            },
        )

    def test_trims_title_and_issue_id(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": " POI-104 ",
                "title": "  Research whitespace handling  ",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-104",
                "title": "Cursor researching: Research whitespace handling",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-105",
                "title": "Already complete",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-106",
                "title": "Comment only",
            }
        )

        self.assertIsNone(result)

    def test_ignores_generic_updates_without_status_field_changes(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "identifier": "POI-107",
                    "title": "Only title changed",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_ignores_status_type_metadata_changes(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["statusType"],
                "data": {
                    "identifier": "POI-108",
                    "title": "Status metadata only",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_ignores_already_prefixed_title_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-109",
                "title": "cursor researching: Existing prefix",
            }
        )

        self.assertIsNone(result)

    def test_ignores_payloads_missing_required_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-110",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
