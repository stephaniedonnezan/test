import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_flat_status_change_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4528",
            "title": "Performance improvement for graph traversal",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4528",
                "title": "Cursor researching: Performance improvement for graph traversal",
            },
        )

    def test_reads_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4528",
                "title": "Investigate delivery graph performance",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4528",
                "title": "Cursor researching: Investigate delivery graph performance",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4528",
            "title": "Performance improvement",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4528",
            "title": "Performance improvement",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-4528",
            "title": "cursor researching: Performance improvement",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_target_status_variants(self):
        for status in ("to_research", "to-research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4528",
                    "title": "Performance improvement",
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-4528",
                        "title": "Cursor researching: Performance improvement",
                    },
                )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "webhookType": "issue",
            "data": {
                "issue": {
                    "identifier": "POI-4528",
                    "title": "Performance improvement",
                    "state": {"name": "Backlog"},
                }
            },
            "updatedFields": ["state"],
            "changes": {"state": {"from": {"name": "Backlog"}, "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4528",
                "title": "Cursor researching: Performance improvement",
            },
        )

    def test_requires_status_field_for_generic_issue_updates(self):
        event = {
            "action": "update",
            "webhookType": "issue",
            "data": {
                "issue": {
                    "identifier": "POI-4528",
                    "title": "Performance improvement",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_changed_status_over_current_status(self):
        event = {
            "action": "update",
            "webhookType": "issue",
            "data": {
                "issue": {
                    "identifier": "POI-4528",
                    "title": "Performance improvement",
                    "state": {"name": "Canceled"},
                }
            },
            "updatedFields": ["workflowState"],
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4528",
                "title": "Cursor researching: Performance improvement",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "No id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-4528"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4528",
                "title": "Performance improvement",
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
                "issueId": "POI-4528",
                "title": "Cursor researching: Performance improvement",
            },
        )


if __name__ == "__main__":
    unittest.main()
