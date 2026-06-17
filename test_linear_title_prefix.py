import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5034",
                "title": "Supply contracts (foundation for inputs/meters)",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5034",
                "title": "Cursor researching: Supply contracts (foundation for inputs/meters)",
            },
        )

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-1",
            "title": "Research queue item",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research queue item",
        )

    def test_uses_current_state_name_for_direct_status_change_events(self):
        event = {
            "trigger": "state_changed",
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_supports_linear_update_when_updated_fields_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "id": "POI-3",
                    "title": "Generic update",
                    "status": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Generic update",
        )

    def test_reads_new_status_from_changes_metadata(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "id": "POI-4",
                    "title": "Workflow status",
                    "workflowState": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow status",
        )

    def test_reads_new_status_from_changed_field_records(self):
        event = {
            "action": "update",
            "changedFields": [
                {"field": "state", "oldValue": "Backlog", "newValue": {"name": "To Research"}}
            ],
            "issueId": "POI-5",
            "title": "Changed field record",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed field record",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-6",
            "title": "Already past research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_updates(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-7",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-8",
            "title": "Commented issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_main_prints_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "CLI issue",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
