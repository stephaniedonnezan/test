import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2649",
                "title": "[1000]Auditor invite/registration/confirmation process is hectic",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2649",
                "title": (
                    "Cursor researching: "
                    "[1000]Auditor invite/registration/confirmation process is hectic"
                ),
            },
        )

    def test_accepts_status_separators_and_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": "POI-1",
                "title": "Needs investigation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Needs investigation",
            },
        )

    def test_skips_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2649",
                "title": "Auditor registration loop",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2",
                "title": "Comment only",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "cursor researching: Already marked",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_accepts_changes_payload_new_status_value(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "changes": {"workflowState": {"from": "Todo", "to": {"name": "to_research"}}},
            "issue": {
                "id": "POI-5",
                "title": "Workflow status payload",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5",
                "title": "Cursor researching: Workflow status payload",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_for_stdin_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "CLI payload",
            }
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
                "issueId": "POI-6",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
