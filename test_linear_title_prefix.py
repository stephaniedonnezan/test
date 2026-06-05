import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_payload_when_status_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
                "newStatus": "to research",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "issueId": "POI-1",
            "title": "Research this",
            "newStatus": "To-Research",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research this",
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
                "newStatus": "In Review",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "id": "POI-1",
            "title": "Research this",
            "newStatus": "to research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "webhook-event-id",
                "issue": {
                    "id": "linear-issue-uuid",
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
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_supports_status_values_from_changes(self):
        event = {
            "type": "Issue Updated",
            "id": "POI-2",
            "title": "Investigate",
            "changes": {
                "workflowState": {
                    "oldValue": "Todo",
                    "newValue": "To Research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate",
            },
        )

    def test_does_not_use_updated_from_as_target_status(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": "To Research"},
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Moved out of research",
                    "state": {"name": "In Progress"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "id": "POI-1",
            "title": "cursor researching: Research this",
            "newStatus": "to research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "title": "No issue ID",
                    "newStatus": "to research",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "id": "POI-1",
                    "newStatus": "to research",
                }
            )
        )

    def test_wrapper_uses_same_handler(self):
        event = {
            "trigger": "status_changed",
            "id": "POI-1",
            "title": "Research this",
            "newStatus": "to research",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_reads_json_from_stdin(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
                "newStatus": "to research",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )


if __name__ == "__main__":
    unittest.main()
