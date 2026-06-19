import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5063",
            "title": "Improve performance of getPossibleQualifiedOutputItemsForLoadingEvent()",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": (
                    "Cursor researching: Improve performance of "
                    "getPossibleQualifiedOutputItemsForLoadingEvent()"
                ),
            },
        )

    def test_supports_cloud_automation_trigger_context_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to_research",
                    "id": "POI-5063",
                    "title": "Research loading event candidates",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Research loading event candidates",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-5063",
            "title": "Improve loading event performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5063",
            "title": "Improve loading event performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-5063",
            "title": "cursor researching: Improve loading event performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-5063",
                    "title": "Improve loading event performance",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Improve loading event performance",
            },
        )

    def test_change_object_new_status_wins_over_stale_issue_state(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5063",
                    "title": "Improve loading event performance",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Improve loading event performance",
            },
        )

    def test_ignores_generic_updates_without_status_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "newStatus": "To Research",
            "id": "POI-5063",
            "title": "Improve loading event performance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_status_id_update_metadata_with_current_workflow_state(self):
        event = {
            "action": "update",
            "updatedFrom": {"workflowStateId": "old-state-id"},
            "data": {
                "issue": {
                    "identifier": "POI-5063",
                    "title": "Improve loading event performance",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Improve loading event performance",
            },
        )

    def test_invalid_payloads_are_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))

    def test_cli_outputs_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5063",
            "title": "Improve loading event performance",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Improve loading event performance",
            },
        )


if __name__ == "__main__":
    unittest.main()
