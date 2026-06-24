import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_cursor_status_changed_to_research_adds_prefix(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5106",
                    "title": "Phase 5: Documentation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5106",
                "title": "Cursor researching: Phase 5: Documentation",
            },
        )

    def test_status_name_is_normalized(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-1",
                "title": "Investigate extraction",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate extraction",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-2",
                "title": "Review docs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Review comments",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4",
                "title": "cursor researching: Already queued",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_linear_update_payload_uses_nested_issue_and_state(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Audit balance extraction",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Audit balance extraction",
            },
        )

    def test_linear_changes_payload_uses_new_value(self):
        event = {
            "type": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "to-research"}}},
            "data": {
                "issue": {
                    "id": "issue-123",
                    "title": "Reconcile drawer totals",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Reconcile drawer totals",
        )

    def test_missing_issue_identity_is_ignored(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "No id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "Script demo path",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Script demo path",
            },
        )


if __name__ == "__main__":
    unittest.main()
