import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4703",
                "title": "[Backend] DeliveryTransportSegmentEntity",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: [Backend] DeliveryTransportSegmentEntity",
            },
        )

    def test_ignores_current_done_trigger_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4703",
                "status": "Done",
                "title": "[Backend] DeliveryTransportSegmentEntity",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-1",
                "title": "Comment-only change",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_target_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-2",
                "title": "Implementation task",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "cursor researching: Already prefixed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-4",
                "title": "Variant casing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Variant casing",
        )

    def test_uses_nested_linear_issue_data(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-6",
                    "title": "Description changed",
                    "state": {"name": "To Research"},
                },
                "updatedFields": ["description"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {"identifier": "POI-7", "title": "Changed state"},
                "changes": {
                    "state": {
                        "oldValue": {"name": "Backlog"},
                        "newValue": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed state",
        )

    def test_state_id_change_falls_back_to_issue_state_name(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-12",
                    "title": "Changed state id",
                    "state": {"name": "To Research"},
                },
                "changes": {
                    "stateId": {
                        "oldValue": "old-state-id",
                        "newValue": "new-state-id",
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed state id",
        )

    def test_updated_from_old_status_is_not_treated_as_new_status(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-8",
                    "title": "Moved away from research",
                    "state": {"name": "Done"},
                },
                "updatedFrom": {"state": {"name": "To Research"}},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_workflow_state_name(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-9",
                    "title": "Workflow state",
                    "workflowState": {"name": "To Research"},
                },
                "updatedFields": [{"field": "workflowState"}],
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow state",
        )

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-10",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-11",
                "title": "CLI task",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-11",
                "title": "Cursor researching: CLI task",
            },
        )


if __name__ == "__main__":
    unittest.main()
