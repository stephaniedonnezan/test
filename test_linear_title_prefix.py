import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    build_issue_title_update,
    handle_issue_status_changed,
)


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_for_flat_cursor_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_prefixes_title_for_nested_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4579",
                    "title": "MB export corrections",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_supports_linear_issue_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-999",
                    "title": "Investigate feedstock variance",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-999",
                "title": "Cursor researching: Investigate feedstock variance",
            },
        )

    def test_supports_changed_status_payloads(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to research"},
                }
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-123",
                    "title": "Research supplier document flow",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Research supplier document flow",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_updates_must_mention_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-4579",
            "title": "cursor researching: MB export corrections",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "cursor researching: MB export corrections",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": " POI-4579 ",
            "title": "  MB export corrections  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_ignores_missing_title_or_id(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4579",
            "title": "MB export corrections",
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
                "issueId": "POI-4579",
                "title": "Cursor researching: MB export corrections",
            },
        )

    def test_cli_is_silent_for_non_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4579",
            "title": "MB export corrections",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
