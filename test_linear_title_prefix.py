import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_status_changed_to_research_prefixes_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4982",
            "title": "Deliveries lifecycle (production site)",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4982",
                "title": "Cursor researching: Deliveries lifecycle (production site)",
            },
        )

    def test_cursor_trigger_context_payload_prefixes_title(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4982",
                "title": "Deliveries lifecycle (production site)",
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4982")
        self.assertEqual(update["title"], "Cursor researching: Deliveries lifecycle (production site)")

    def test_normalizes_status_separator_and_casing_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issueId": "POI-4982",
            "title": "Deliveries lifecycle (production site)",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4982",
            "title": "Deliveries lifecycle (production site)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4982",
            "title": "Deliveries lifecycle (production site)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4982",
            "title": "cursor researching: Deliveries lifecycle (production site)",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_issue_update_uses_identifier_over_uuid(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4982",
                "title": "Deliveries lifecycle (production site)",
                "state": {"name": "To Research"},
            },
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4982")
        self.assertEqual(update["title"], "Cursor researching: Deliveries lifecycle (production site)")

    def test_nested_linear_issue_object_status_update(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-4982",
                    "title": "Deliveries lifecycle (production site)",
                    "workflowState": {"name": "To Research"},
                }
            },
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-4982")
        self.assertEqual(update["title"], "Cursor researching: Deliveries lifecycle (production site)")

    def test_generic_update_without_status_marker_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4982",
                "title": "Deliveries lifecycle (production site)",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Only title"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4982"}
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4982",
            "title": "Deliveries lifecycle (production site)",
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
                "issueId": "POI-4982",
                "title": "Cursor researching: Deliveries lifecycle (production site)",
            },
        )


if __name__ == "__main__":
    unittest.main()
