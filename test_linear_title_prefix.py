import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Rename the sites and org names in the methane demo",
                "id": "POI-4798",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4798",
                "title": "Cursor researching: Rename the sites and org names in the methane demo",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "title": "Clarify demo naming",
                "issueId": "POI-4798",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Clarify demo naming",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "Clarify demo naming",
                "id": "POI-4798",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Clarify demo naming",
                "id": "POI-4798",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "cursor researching: Clarify demo naming",
                "id": "POI-4798",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_with_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "issue": {
                    "identifier": "POI-4798",
                    "title": "Clarify demo naming",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {"state": {"from": "Backlog", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4798",
                "title": "Cursor researching: Clarify demo naming",
            },
        )

    def test_requires_status_marker_for_generic_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4798",
                    "title": "Clarify demo naming",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_workflow_state_object_when_updated_fields_mark_status(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4798",
                    "title": "Clarify demo naming",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Clarify demo naming",
        )

    def test_returns_none_when_issue_id_or_title_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4798"}
            )
        )

    def test_cli_prints_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Clarify demo naming",
                "id": "POI-4798",
            },
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
                "issueId": "POI-4798",
                "title": "Cursor researching: Clarify demo naming",
            },
        )


if __name__ == "__main__":
    unittest.main()
