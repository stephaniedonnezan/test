import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4976",
                "title": "Invite-Form fields Needs UI Refinements",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4976",
                "title": "Cursor researching: Invite-Form fields Needs UI Refinements",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-4976",
                "title": "Invite-Form fields Needs UI Refinements",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4976",
                "title": "Invite-Form fields Needs UI Refinements",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4976",
                "title": "cursor researching: Invite-Form fields Needs UI Refinements",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "to_research",
                "issueId": "POI-4976",
                "title": "Invite-Form fields Needs UI Refinements",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Invite-Form fields Needs UI Refinements",
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4976",
                    "title": "Invite-Form fields Needs UI Refinements",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4976",
                "title": "Cursor researching: Invite-Form fields Needs UI Refinements",
            },
        )

    def test_handles_changed_status_metadata(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "id": "POI-4976",
                    "title": "Invite-Form fields Needs UI Refinements",
                },
                "changes": {
                    "workflowState": {
                        "from": {"name": "Backlog"},
                        "to": {"name": "to research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Invite-Form fields Needs UI Refinements",
        )

    def test_ignores_generic_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-4976",
                    "title": "Invite-Form fields Needs UI Refinements",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4976",
                    }
                }
            )
        )

    def test_cli_reads_json_from_stdin(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4976",
                "title": "Invite-Form fields Needs UI Refinements",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4976",
                "title": "Cursor researching: Invite-Form fields Needs UI Refinements",
            },
        )


if __name__ == "__main__":
    unittest.main()
