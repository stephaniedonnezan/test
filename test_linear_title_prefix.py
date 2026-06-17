import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5001",
                "title": "Cursor researching: Timezone selector acts as filter",
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        payload = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5001",
                "title": "Timezone selector acts as filter",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5001",
                "title": "Cursor researching: Timezone selector acts as filter",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        payload = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
            "issueId": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Timezone selector acts as filter",
        )

    def test_prefixes_linear_issue_update_when_status_field_changed(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5001",
                    "title": "Timezone selector acts as filter",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5001",
                "title": "Cursor researching: Timezone selector acts as filter",
            },
        )

    def test_reads_status_from_changes_to_value(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "issue": {
                "identifier": "POI-5001",
                "title": "Timezone selector acts as filter",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Timezone selector acts as filter",
        )

    def test_change_target_takes_priority_over_stale_status_field(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "status": "Backlog",
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Timezone selector acts as filter",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_triggers(self):
        payload = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_issue_updates_without_status_change(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_does_not_duplicate_existing_prefix(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5001",
            "title": "cursor researching: Timezone selector acts as filter",
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5001",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Timezone selector acts as filter",
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5001",
            "title": "Timezone selector acts as filter",
        }
        stdout = io.StringIO()

        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-5001",
                "title": "Cursor researching: Timezone selector acts as filter",
            },
        )


if __name__ == "__main__":
    unittest.main()
