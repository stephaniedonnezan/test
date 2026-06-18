import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4981",
                "title": "Super admin",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4981",
                "title": "Cursor researching: Super admin",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4981",
                "title": "Super admin",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Super admin",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4981",
                "title": "Super admin",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4981",
                "title": "Super admin",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4981",
                "title": "cursor researching: Super admin",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4981",
                    "title": "Super admin",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4981",
                "title": "Cursor researching: Super admin",
            },
        )

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4981",
                    "title": "Super admin",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"newValue": {"name": "to-research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4981",
                    "title": "Super admin",
                    "state": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Super admin",
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4981",
                "title": "Super admin",
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
                "issueId": "POI-4981",
                "title": "Cursor researching: Super admin",
            },
        )


if __name__ == "__main__":
    unittest.main()
