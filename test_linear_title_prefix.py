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
                "newStatus": "to research",
                "id": "POI-3398",
                "title": "Default values for incoming pos attributes of e-Methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3398",
                "title": (
                    "Cursor researching: "
                    "Default values for incoming pos attributes of e-Methane"
                ),
            },
        )

    def test_prefixes_top_level_status_change_to_research(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "identifier": "POI-123",
            "title": "Investigate data sync",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate data sync",
            },
        )

    def test_prefixes_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Research supplier matching",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Research supplier matching",
            },
        )

    def test_changes_payload_supplies_new_status(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": {"name": "to research"}}},
            "data": {
                "issue": {
                    "id": "linear-id-789",
                    "title": "Review methane calculations",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-id-789",
                "title": "Cursor researching: Review methane calculations",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3398",
                "title": "Default values for incoming pos attributes of e-Methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3398",
                "title": "Default values for incoming pos attributes of e-Methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-789",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3398",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing identifier",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-999",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_event(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-3398",
                "title": "Default values for incoming pos attributes of e-Methane",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3398",
                "title": (
                    "Cursor researching: "
                    "Default values for incoming pos attributes of e-Methane"
                ),
            },
        )

    def test_cli_prints_nothing_for_non_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3398",
                "title": "Default values for incoming pos attributes of e-Methane",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
