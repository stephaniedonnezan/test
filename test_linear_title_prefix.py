import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Error alert repeats for high GO amount",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Error alert repeats for high GO amount",
            },
        )

    def test_uses_trigger_context_wrapped_by_cloud_event(self):
        event = {
            "automationId": "automation-1",
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5018",
                    "title": "Research title update",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Research title update",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-5018",
            "title": "Do not update this title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_triggers(self):
        event = {
            "trigger": "assignee_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "Do not update this title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_variants(self):
        for status in ("toResearch", "TO_RESEARCH", "to-research"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-5018",
                    "title": "Variant status title",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Variant status title",
                )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "cursor researching: Existing title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing title",
        )

    def test_builds_update_for_nested_linear_issue_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5018",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_extracts_status_from_linear_change_payload(self):
        event = {
            "action": "updated",
            "data": {
                "identifier": "POI-5018",
                "title": "Changed status payload",
            },
            "changes": {
                "status": {
                    "from": "Backlog",
                    "to": "To Research",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status payload",
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5018",
                "title": "Title-only update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_title = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
        }
        missing_id = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(missing_title))
        self.assertIsNone(build_issue_title_update(missing_id))


class CliTest(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5018",
            "title": "CLI issue",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            encoding="utf-8",
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5018",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
