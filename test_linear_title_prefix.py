import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4884",
                "title": "lock qualified outputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4884",
                "title": "Cursor researching: lock qualified outputs",
            },
        )

    def test_accepts_status_casing_and_separator_variants(self):
        event = {
            "triggerContext": {
                "webhookType": "statusChanged",
                "new_status": "to-research",
                "identifier": "POI-1",
                "title": "Handle status variants",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Handle status variants",
            },
        )

    def test_accepts_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Nested payload",
                    "state": {"name": "Backlog"},
                },
                "updatedFields": ["state"],
                "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_accepts_changed_fields_mapping(self):
        event = {
            "type": "Issue Updated",
            "issue": {
                "id": "linear-id",
                "title": "Mapping fields",
                "workflowState": {"name": "To Research"},
            },
            "changedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-id",
                "title": "Cursor researching: Mapping fields",
            },
        )

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3",
                "title": "Comment event",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_destination_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4",
                "title": "Review issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "data": {
                "issue": {"identifier": "POI-5", "title": "Label update", "state": {"name": "To Research"}},
                "updatedFields": ["labels"],
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-6",
                "title": "cursor researching: Existing prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-7",
                "title": " ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-8",
                "title": "CLI issue",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
