import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_current_cloud_trigger_context_when_status_becomes_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "QA report - POI-4579",
                "id": "POI-5091",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5091",
                "title": "Cursor researching: QA report - POI-4579",
            },
        )

    def test_ignores_current_cloud_trigger_context_when_status_is_done(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "QA report - POI-4579",
                "id": "POI-5091",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_and_trigger_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-1",
            "title": "Research separator handling",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research separator handling",
        )

    def test_prefixes_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["status"],
            "data": {
                "issue": {
                    "identifier": "POI-2",
                    "title": "Handle Linear webhook shape",
                    "status": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Handle Linear webhook shape",
            },
        )

    def test_prefixes_when_new_status_is_in_changes_container(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Read status from changes",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Read status from changes",
        )

    def test_uses_identifier_before_linear_uuid(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "data": {
                "issue": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "identifier": "POI-4",
                    "title": "Prefer issue identifier",
                }
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4")

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Do not prefix on comments",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-6",
            "title": "Title-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "cursor researching: Already marked",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-8"}
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action_as_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "Smoke test CLI",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-9",
                "title": "Cursor researching: Smoke test CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
