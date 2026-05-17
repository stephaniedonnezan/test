import json
import subprocess
import sys
import unittest

from scripts.linear_research_title import (
    TITLE_PREFIX,
    add_research_prefix,
    build_title_update,
)


class LinearResearchTitleTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_payload(self):
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4347",
                "title": "When adding meter readings one by one, it creates duplicates",
            }
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "POI-4347")
        self.assertEqual(
            update.new_title,
            (
                f"{TITLE_PREFIX}: When adding meter readings one by one, "
                "it creates duplicates"
            ),
        )

    def test_builds_update_for_flat_status_changed_payload(self):
        payload = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-1234",
            "title": "Research this issue",
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "POI-1234")
        self.assertEqual(update.new_title, f"{TITLE_PREFIX}: Research this issue")

    def test_skips_other_statuses(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4347",
                "title": "When adding meter readings one by one, it creates duplicates",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_skips_non_status_change_events(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4347",
                "title": "When adding meter readings one by one, it creates duplicates",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_skips_titles_that_already_start_with_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4347",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_supports_linear_updated_fields_payloads(self):
        payload = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4347",
                "title": "Investigate meter reading duplicates",
                "state": {"name": "to_research"},
            },
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "issue-uuid")
        self.assertEqual(
            update.new_title,
            f"{TITLE_PREFIX}: Investigate meter reading duplicates",
        )

    def test_supports_linear_updated_from_payloads(self):
        payload = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "title": "Investigate meter reading duplicates",
                "state": {"name": "to research"},
            },
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "issue-uuid")
        self.assertEqual(
            update.new_title,
            f"{TITLE_PREFIX}: Investigate meter reading duplicates",
        )

    def test_issue_update_must_include_status_field_change(self):
        payload = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Investigate meter reading duplicates",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_title_update(payload))

    def test_new_status_takes_precedence_over_stale_status_fields(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "Todo",
            },
            "newStatus": "to research",
            "id": "POI-4347",
            "title": "Investigate meter reading duplicates",
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(
            update.new_title,
            f"{TITLE_PREFIX}: Investigate meter reading duplicates",
        )

    def test_add_research_prefix_is_idempotent(self):
        self.assertEqual(
            add_research_prefix("cursor researching: Existing title"),
            "cursor researching: Existing title",
        )

    def test_cli_dry_run_outputs_update(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4347",
            "title": "CLI title",
        }

        completed = subprocess.run(
            [sys.executable, "scripts/linear_research_title.py", "--dry-run"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("POI-4347", completed.stdout)
        self.assertIn(f"{TITLE_PREFIX}: CLI title", completed.stdout)


if __name__ == "__main__":
    unittest.main()
