import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5003",
            "title": "Trading vs Production Filter not filtering",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )

    def test_prefixes_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5003",
                "title": "Trading vs Production Filter not filtering",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )

    def test_prefixes_generic_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5003",
                    "title": "Trading vs Production Filter not filtering",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )

    def test_reads_new_status_from_changes_metadata(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5003",
                    "title": "Trading vs Production Filter not filtering",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )

    def test_combines_outer_trigger_with_nested_issue_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "data": {
                "issue": {
                    "identifier": "POI-5003",
                    "title": "Trading vs Production Filter not filtering",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-5003",
            "title": "Trading vs Production Filter not filtering",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5003",
            "title": "Trading vs Production Filter not filtering",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-5003",
            "title": "Trading vs Production Filter not filtering",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5003",
            "title": "cursor researching: Trading vs Production Filter not filtering",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5003",
                }
            )
        )

        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Trading vs Production Filter not filtering",
                }
            )
        )

    def test_cli_prints_title_update_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5003",
            "title": "Trading vs Production Filter not filtering",
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
                "issueId": "POI-5003",
                "title": "Cursor researching: Trading vs Production Filter not filtering",
            },
        )


if __name__ == "__main__":
    unittest.main()
