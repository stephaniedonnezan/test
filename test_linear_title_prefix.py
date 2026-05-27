import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_prefixes_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_cursor_trigger_context_payload_is_supported(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4751",
                "title": "Research me",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Research me",
            },
        )

    def test_status_normalization_accepts_common_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4751",
                    "title": "Normalize status",
                }

                result = build_issue_title_update(event)

                self.assertIsNotNone(result)
                self.assertEqual(result["title"], "Cursor researching: Normalize status")

    def test_non_target_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_is_ignored(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "cursor researching: Knowledge support",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Knowledge support on a POS-related question",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_with_status_field_is_supported(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-id",
                "identifier": "POI-4751",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_linear_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-id",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_changed_field_objects_are_supported(self):
        event = {
            "action": "Issue Updated",
            "changes": [{"field": "workflowState"}],
            "data": {
                "issueId": "POI-4751",
                "title": "Workflow issue",
                "workflowState": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Workflow issue",
            },
        )

    def test_issue_id_and_title_are_trimmed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issue_id": " POI-4751 ",
            "title": " Knowledge support ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support",
            },
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_json_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4751",
            "title": "CLI issue",
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
                "issueId": "POI-4751",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
