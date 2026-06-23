import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_flat_cursor_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5103",
            "title": "Backend trader demo seeder",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5103",
                "title": "Cursor researching: Backend trader demo seeder",
            },
        )

    def test_nested_automation_trigger_info_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5103",
                    "title": "Phase 2 backend work",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5103",
                "title": "Cursor researching: Phase 2 backend work",
            },
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to_research",
                "id": "POI-42",
                "title": "Fallback status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fallback status",
        )

    def test_handle_issue_status_changed_alias(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "identifier": "POI-1",
            "title": "Camel case status",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5103",
            "title": "Backend trader demo seeder",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5103",
            "title": "Backend trader demo seeder",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5103",
            "title": "cursor researching: Backend trader demo seeder",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "  POI-5103  ",
            "title": "  Backend trader demo seeder  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5103",
                "title": "Cursor researching: Backend trader demo seeder",
            },
        )

    def test_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5103",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5103",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_generic_update_without_status_marker_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-5103",
                    "title": "Description update",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_change_value_has_priority_over_stale_issue_state(self):
        event = {
            "type": "Issue Updated",
            "changes": {"state": {"to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5103",
                    "title": "Changed state payload",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed state payload",
        )

    def test_invalid_payloads_are_ignored(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a payload"))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))

    def test_cli_reads_event_from_stdin(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5103",
            "title": "CLI payload",
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
                "issueId": "POI-5103",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
