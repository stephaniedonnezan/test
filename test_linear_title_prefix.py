import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_cursor_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4509",
                "title": "Org user should be able to change audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4509",
                "title": "Cursor researching: Org user should be able to change audit dates",
            },
        )

    def test_supports_top_level_trigger_context_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4510",
                    "title": "Investigate import failures",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-4510")
        self.assertEqual(update["title"], "Cursor researching: Investigate import failures")

    def test_normalizes_status_variants(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4511",
                    "title": "Normalize this status",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Normalize this status",
                )

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4512",
            "title": "cursor researching: Existing prefix",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "cursor researching: Existing prefix")

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4513",
            "title": "Should not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4514",
            "title": "Should not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4515",
            "title": "Should not change",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_linear_issue_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4516",
                "title": "Linear nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4516",
                "title": "Cursor researching: Linear nested issue",
            },
        )

    def test_supports_changed_status_new_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "oldValue": "Backlog",
                    "newValue": "To Research",
                }
            },
            "data": {
                "issueId": "POI-4517",
                "title": "Changed via workflow state",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed via workflow state",
        )

    def test_supports_changed_status_object_new_value(self):
        event = {
            "action": "update",
            "changes": {
                "state": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4520",
                "title": "Object status value",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Object status value",
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4518",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4519",
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
                "issueId": "POI-4519",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
