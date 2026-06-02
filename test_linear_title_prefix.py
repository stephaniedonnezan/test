import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4577",
                "title": "Add lower heating value setting",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4577",
                "title": "Cursor researching: Add lower heating value setting",
            },
        )

    def test_accepts_separator_and_case_variants_for_research_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-4577",
            "title": "Investigate production site settings",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4577",
                "title": "Cursor researching: Investigate production site settings",
            },
        )

    def test_reads_issue_details_from_nested_linear_payload(self):
        event = {
            "id": "webhook-event-id",
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4577",
                "title": "Production site lower heating value setting",
                "state": {"name": "to_research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Production site lower heating value setting",
            },
        )

    def test_detects_status_update_from_updated_from_metadata(self):
        event = {
            "action": "update",
            "updatedFrom": {"workflowStateId": "old-state-id"},
            "data": {
                "identifier": "POI-4577",
                "title": "Research production site settings",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4577",
                "title": "Cursor researching: Research production site settings",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4577",
            "title": "Add lower heating value setting",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4577",
            "title": "Add lower heating value setting",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4577",
                "title": "Add lower heating value setting",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4577",
            "title": "  cursor researching: Add lower heating value setting",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Add lower heating value setting",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4577",
                }
            )
        )

    def test_ignores_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4577",
            "title": "Add lower heating value setting",
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
                "issueId": "POI-4577",
                "title": "Cursor researching: Add lower heating value setting",
            },
        )

    def test_cli_prints_nothing_for_non_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4577",
            "title": "Add lower heating value setting",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
