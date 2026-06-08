import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4849",
                "title": "Make Filters Visible",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4849",
                "title": "Cursor researching: Make Filters Visible",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "identifier": "POI-1111",
                "title": "Investigate allocation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1111",
                "title": "Cursor researching: Investigate allocation",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4849",
                "title": "Make Filters Visible",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_issue_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-2222",
                "title": "Rename only",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3333",
                "title": "cursor researching: Existing research title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_normalized_status_and_trigger_names(self):
        event = {
            "triggerContext": {
                "trigger": "StatusChanged",
                "new_status": "TO-RESEARCH",
                "issue_id": "POI-4444",
                "title": "Normalize inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize inputs",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5555",
                "title": "Nested webhook",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Nested webhook",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["workflowState"],
            "changes": {"workflowState": {"newValue": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-6666",
                "title": "Changed workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed workflow state",
        )

    def test_returns_none_for_missing_title_or_issue_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "to research"}}
            )
        )

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7777",
                "title": "CLI sample",
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
                "issueId": "POI-7777",
                "title": "Cursor researching: CLI sample",
            },
        )


if __name__ == "__main__":
    unittest.main()
