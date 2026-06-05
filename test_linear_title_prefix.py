import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_returns_title_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4800",
                "title": "MB Grid Consumption zeros",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_handle_issue_status_changed_alias_uses_same_handler(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_non_research_status_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4800",
                "title": "MB Grid Consumption zeros",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_change_trigger_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4800",
                "title": "MB Grid Consumption zeros",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_already_prefixed_title_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4800",
                "title": "cursor researching: MB Grid Consumption zeros",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_current_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4800",
                "title": "MB Grid Consumption zeros",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_nested_change_to_value_is_used_for_target_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4800",
                    "title": "MB Grid Consumption zeros",
                    "state": {"name": "Backlog"},
                }
            },
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_updated_from_is_evidence_but_not_target_status(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": "To Research"},
            "data": {
                "identifier": "POI-4800",
                "title": "MB Grid Consumption zeros",
                "state": {"name": "In Progress"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_to_research_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "issue_id": "POI-4800",
            "title": "MB Grid Consumption zeros",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: MB Grid Consumption zeros",
        )

    def test_missing_issue_id_or_title_returns_none(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4800"}
            )
        )

    def test_non_mapping_payload_returns_none(self):
        self.assertIsNone(build_issue_title_update(None))


class CommandLineInterfaceTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4800",
                "title": "MB Grid Consumption zeros",
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
                "issueId": "POI-4800",
                "title": "Cursor researching: MB Grid Consumption zeros",
            },
        )

    def test_cli_prints_null_for_non_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4800",
                "title": "MB Grid Consumption zeros",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIsNone(json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
