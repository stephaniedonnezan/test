import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_trigger_context_builds_title_update(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4425",
                "title": "[]Rounding logic",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4425",
                "title": "Cursor researching: []Rounding logic",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-1",
            "title": "Research this",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "Cursor researching: Research this")

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4425",
            "title": "[]Rounding logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "status": "to research",
            "id": "POI-4425",
            "title": "[]Rounding logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4425",
            "title": "cursor researching: []Rounding logic",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "cursor researching: []Rounding logic")

    def test_nested_linear_update_uses_issue_data(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-internal-id",
                "identifier": "POI-4425",
                "title": "[]Rounding logic",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4425",
                "title": "Cursor researching: []Rounding logic",
            },
        )

    def test_nested_linear_update_does_not_use_webhook_event_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-issue-id",
                "title": "[]Rounding logic",
                "state": {"name": "To Research"},
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "linear-issue-id")

    def test_generic_issue_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4425",
                "title": "[]Rounding logic",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_change_object(self):
        event = {
            "action": "update",
            "type": "Issue",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "identifier": "POI-4425",
                "title": "[]Rounding logic",
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4425")
        self.assertEqual(update["title"], "Cursor researching: []Rounding logic")

    def test_returns_none_without_issue_title_or_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4425",
            "title": "[]Rounding logic",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4425",
                "title": "Cursor researching: []Rounding logic",
            },
        )


if __name__ == "__main__":
    unittest.main()
