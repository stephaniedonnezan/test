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
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5058",
                "title": "Move the mb-data-manager into the psqo module",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "issueId": "POI-5058",
            "title": "cursor researching: Move the mb-data-manager into the psqo module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "status-change",
            "new_status": "to_research",
            "issue_id": " POI-5058 ",
            "title": " Move the mb-data-manager into the psqo module ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_supports_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_supports_generic_update_changes_object(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                }
            },
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_cloud_automation_trigger_info(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5058",
                    "title": "Move the mb-data-manager into the psqo module",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Move the mb-data-manager into the psqo module",
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Move the mb-data-manager into the psqo module",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-5058",
            "title": "Move the mb-data-manager into the psqo module",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5058",
                "title": "Cursor researching: Move the mb-data-manager into the psqo module",
            },
        )


if __name__ == "__main__":
    unittest.main()
