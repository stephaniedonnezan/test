import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_status_changed_to_research_builds_title_update(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4996",
            "title": "Created a container and added a loading event -> not visible",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4996",
                "title": "Cursor researching: Created a container and added a loading event -> not visible",
            },
        )

    def test_accepts_wrapped_cursor_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4996",
                "title": "Investigate container events",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4996",
                "title": "Cursor researching: Investigate container events",
            },
        )

    def test_status_matching_is_case_separator_and_camel_case_insensitive(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "identifier": "POI-1",
            "title": "Review trade flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Review trade flow",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4996",
            "title": "Created a container and added a loading event -> not visible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4996",
            "title": "Created a container and added a loading event -> not visible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_marker(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4996",
            "title": "cursor researching: Created a container and added a loading event -> not visible",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-4996",
                    "title": "Created a container and added a loading event -> not visible",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4996",
                "title": "Cursor researching: Created a container and added a loading event -> not visible",
            },
        )

    def test_nested_linear_update_ignores_unrelated_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4996",
                    "title": "Created a container and added a loading event -> not visible",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_can_be_read_from_change_details(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": {"name": "to_research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4996",
                    "title": "Container not visible in allocation",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4996",
                "title": "Cursor researching: Container not visible in allocation",
            },
        )

    def test_alias_uses_same_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4996",
            "title": "Investigate loading event",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4996",
            "title": "Investigate loading event",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4996",
                "title": "Cursor researching: Investigate loading event",
            },
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
