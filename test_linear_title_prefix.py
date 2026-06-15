import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_for_flat_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4872",
                "title": "Issues indicator is mispositioned",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4872",
                "title": "Cursor researching: Issues indicator is mispositioned",
            },
        )

    def test_accepts_status_variants_case_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4872",
            "title": "Container issues panel",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4872",
                "title": "Cursor researching: Container issues panel",
            },
        )

    def test_ignores_other_target_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-4872",
                "title": "Issues indicator is mispositioned",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4872",
            "title": "Issues indicator is mispositioned",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4872",
            "title": "cursor researching: Issues indicator is mispositioned",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_payload_with_status_change(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-4872",
                    "title": "Issues indicator is mispositioned",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Issues indicator is mispositioned",
            },
        )

    def test_accepts_changed_to_status_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "id": "POI-4872",
                    "title": "Issues indicator is mispositioned",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4872",
                "title": "Cursor researching: Issues indicator is mispositioned",
            },
        )

    def test_returns_none_when_required_issue_fields_are_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Issues indicator is mispositioned",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_reads_json_from_stdin(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4872",
                "title": "Issues indicator is mispositioned",
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
                "issueId": "POI-4872",
                "title": "Cursor researching: Issues indicator is mispositioned",
            },
        )


if __name__ == "__main__":
    unittest.main()
