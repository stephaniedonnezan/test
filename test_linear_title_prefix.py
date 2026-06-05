import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_flat_cursor_status_change_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4818",
                "title": "If manual allocation doesn't 100% match",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4818",
                "title": "Cursor researching: If manual allocation doesn't 100% match",
            },
        )

    def test_wrapper_matches_primary_entrypoint(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Research target",
            }
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4818",
                "title": "Allocation mismatch",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4818",
                "title": "Allocation mismatch",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4818",
                "title": "cursor researching: Allocation mismatch",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "id": "POI-4818",
                "title": "Allocation mismatch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allocation mismatch",
        )

    def test_uses_current_nested_linear_state_for_status_update_webhook(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4818",
                "title": "Allocation mismatch",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4818",
                "title": "Cursor researching: Allocation mismatch",
            },
        )

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "identifier": "POI-4818",
                "title": "Allocation mismatch",
            },
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allocation mismatch",
        )

    def test_uses_status_fallback_for_direct_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "ToResearch",
                "id": "POI-4818",
                "title": "Allocation mismatch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allocation mismatch",
        )

    def test_updated_from_only_does_not_supply_target_status(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"state": {"name": "To Research"}},
            "data": {
                "identifier": "POI-4818",
                "title": "Allocation mismatch",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Allocation mismatch",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4818",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
