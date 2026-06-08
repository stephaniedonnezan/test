import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_alias_uses_same_handler(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-1",
                "title": "Investigate export",
            },
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_unrelated_trigger_even_with_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "identifier": "POI-99",
                "title": "  Research this  ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-99",
                "title": "Cursor researching: Research this",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "cursor researching: []MB Grid Consumption zeros",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_update_payload(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "identifier": "POI-4800",
                    "title": "[]MB Grid Consumption zeros",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_handles_changes_new_value_status_payload(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4800",
                    "title": "[]MB Grid Consumption zeros",
                }
            },
            "changes": {"status": {"oldValue": "Todo", "newValue": "to_research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_ignores_updated_from_previous_research_status(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "updatedFrom": {"state": {"name": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4800",
                    "title": "[]MB Grid Consumption zeros",
                    "state": {"name": "In Progress"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4800",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Missing id",
                    }
                }
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a mapping"))  # type: ignore[arg-type]

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            },
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(json.loads(completed.stdout), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
