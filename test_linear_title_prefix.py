import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cloud_status_changed_to_research_updates_title(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5033",
                "title": "Cursor researching: CO2 inputs optional proof file",
            },
        )

    def test_current_in_progress_trigger_does_not_update(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "In Progress",
                    "id": "POI-5033",
                    "title": "CO2 inputs optional proof file",
                }
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_direct_trigger_context_payload_updates_title(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-100",
                "title": "Investigate supplier imports",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Investigate supplier imports",
            },
        )

    def test_linear_update_payload_with_state_change_updates_title(self):
        event = {
            "action": "update",
            "data": {
                "id": "linear-internal-id",
                "identifier": "POI-200",
                "title": "Check RFNBO status",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-200",
                "title": "Cursor researching: Check RFNBO status",
            },
        )

    def test_changes_payload_with_new_status_updates_title(self):
        event = {
            "type": "Issue Updated",
            "issue": {"identifier": "POI-300", "title": "Document title behavior"},
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-300",
                "title": "Cursor researching: Document title behavior",
            },
        )

    def test_prefers_explicit_new_status_over_stale_outer_status(self):
        event = {
            "trigger": "status_changed",
            "status": "In Progress",
            "triggerContext": {
                "newStatus": "To Research",
                "id": "POI-400",
                "title": "Resolve stale wrapper state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-400",
                "title": "Cursor researching: Resolve stale wrapper state",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-500",
            "title": "cursor researching: Existing research title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_ignored_even_with_new_status(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-600",
            "title": "Should not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_update_without_status_field_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-700",
            "title": "Title-only edit",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-800"}
            )
        )

    def test_non_mapping_payload_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-900",
            "title": "Smoke test CLI",
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
                "issueId": "POI-900",
                "title": "Cursor researching: Smoke test CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
