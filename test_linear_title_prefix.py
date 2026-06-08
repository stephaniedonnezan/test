import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "(WIP) QA report POI-4483 Gather ETS daily prices",
                "id": "POI-4837",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: (WIP) QA report POI-4483 Gather ETS daily prices",
            },
        )

    def test_flat_status_changed_event_to_research(self):
        event = {
            "trigger": "statusChanged",
            "status": "to research",
            "title": "Investigate retry behavior",
            "issueId": "POI-1",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate retry behavior",
            },
        )

    def test_nested_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-2",
                "title": "Research settlement mismatch",
                "state": {"name": "to_research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Research settlement mismatch",
            },
        )

    def test_nested_issue_id_wins_over_outer_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Research authorization timeout",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Research authorization timeout",
            },
        )

    def test_nested_issue_title_wins_over_outer_webhook_title(self):
        event = {
            "title": "Webhook envelope title",
            "trigger": "status_changed",
            "status": "To Research",
            "issue": {
                "id": "POI-7",
                "title": "Investigate webhook issue title",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Investigate webhook issue title",
            },
        )

    def test_normalizes_to_research_variants(self):
        for status in ("to-research", "to_research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "status": status,
                    "title": "Check terminal batching",
                    "id": "POI-3",
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-3",
                        "title": "Cursor researching: Check terminal batching",
                    },
                )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "UBA POS: version number is not incremented",
                "id": "POI-4839",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update(self):
        event = {
            "action": "update",
            "data": {
                "id": "POI-4",
                "title": "Investigate order export",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"title": "Old title"},
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_research_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "title": "cursor researching: Investigate duplicate prefix",
            "id": "POI-5",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "status": "To Research", "id": "POI-6"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "status": "To Research", "title": "No id"})
        )

    def test_cli_outputs_update_action_for_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Gather ETS daily prices",
                "id": "POI-4837",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_cli_returns_nonzero_when_no_update_is_needed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Gather ETS daily prices",
                "id": "POI-4837",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
