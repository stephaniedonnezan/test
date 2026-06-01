import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_trigger(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3936",
            "title": "Show Production Site Mass Balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )

    def test_accepts_cursor_trigger_context_shape(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-3936",
                "title": "Show Production Site Mass Balance",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )

    def test_accepts_camel_case_research_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-3936",
            "title": "Show Production Site Mass Balance",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-3936",
                "title": "Show Production Site Mass Balance",
                "state": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )

    def test_nested_issue_id_takes_precedence_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-3936",
                "title": "Show Production Site Mass Balance",
                "state": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )

    def test_generic_issue_update_without_updated_status_field_is_ignored(self):
        event = {
            "action": "update",
            "data": {
                "identifier": "POI-3936",
                "title": "Show Production Site Mass Balance",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3936",
            "title": "Show Production Site Mass Balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3936",
            "title": "Show Production Site Mass Balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": "POI-3936",
            "title": "cursor researching: Show Production Site Mass Balance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3936"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Title"}
            )
        )

    def test_cli_prints_update_action_for_json_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3936",
            "title": "Show Production Site Mass Balance",
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
                "issueId": "POI-3936",
                "title": "Cursor researching: Show Production Site Mass Balance",
            },
        )


if __name__ == "__main__":
    unittest.main()
