import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_prefixes_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5036",
            "title": "Mass Balance canvas items in delivery opacity off",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5036",
                "title": "Cursor researching: Mass Balance canvas items in delivery opacity off",
            },
        )

    def test_cloud_trigger_context_payload_is_supported(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-1234",
                    "title": "Investigate inventory allocation",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1234",
                "title": "Cursor researching: Investigate inventory allocation",
            },
        )

    def test_status_and_trigger_names_are_normalized(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "identifier": "POI-42",
            "title": "Normalize incoming status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize incoming status names",
        )

    def test_non_research_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-5036",
            "title": "Mass Balance canvas items in delivery opacity off",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5036",
            "title": "Mass Balance canvas items in delivery opacity off",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "cursor researching: Already queued",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Already queued",
        )

    def test_title_and_issue_id_are_trimmed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-99 ",
            "title": "  Trim whitespace  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-99",
                "title": "Cursor researching: Trim whitespace",
            },
        )

    def test_linear_update_with_updated_fields_and_nested_issue_is_supported(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "uuid-123",
                    "identifier": "POI-55",
                    "title": "Nested issue payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-55",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_linear_update_with_updated_from_state_id_is_supported(self):
        event = {
            "action": "Issue Updated",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "uuid-456",
                "identifier": "POI-56",
                "title": "Updated from payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-56")

    def test_change_object_new_value_is_used_for_status(self):
        event = {
            "type": "Updated Issue",
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
            "issue": {
                "identifier": "POI-57",
                "title": "Changed status object",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status object",
        )

    def test_generic_update_without_status_change_marker_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-58",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "title": "No id"})
        )
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"})
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class CliTest(unittest.TestCase):
    def test_cli_emits_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5036",
            "title": "CLI sample",
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
                "issueId": "POI-5036",
                "title": "Cursor researching: CLI sample",
            },
        )


if __name__ == "__main__":
    unittest.main()
