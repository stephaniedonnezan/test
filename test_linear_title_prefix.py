import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_research_prefix_for_flat_status_change_event(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_cursor_automation_trigger_context(self):
        action = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-1",
                    "title": "Investigate matching behavior",
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-1")
        self.assertEqual(action["title"], "Cursor researching: Investigate matching behavior")

    def test_accepts_nested_linear_issue_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-2",
                        "title": "Review certificate allocation",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-2")
        self.assertEqual(action["title"], "Cursor researching: Review certificate allocation")

    def test_accepts_updated_from_state_id_as_status_change(self):
        action = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFrom": {"stateId": "old-state-id"},
                "data": {
                    "id": "issue-uuid",
                    "identifier": "POI-3",
                    "title": "Clarify emissions rules",
                    "workflowState": {"name": "to_research"},
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-3")
        self.assertEqual(action["title"], "Cursor researching: Clarify emissions rules")

    def test_accepts_case_and_separator_variants(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issue_id": "POI-4",
                "title": "Check contract edge case",
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Check contract edge case")

    def test_ignores_other_statuses(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-5",
                "title": "Build the feature",
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_update_events(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "newStatus": "to research",
                "id": "POI-6",
                "title": "Rename issue",
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_existing_prefix(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
                "title": "cursor researching: Already queued",
            }
        )

        self.assertIsNone(action)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-8",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_cli_prints_action_for_valid_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "Check CLI",
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
                "issueId": "POI-9",
                "title": "Cursor researching: Check CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
