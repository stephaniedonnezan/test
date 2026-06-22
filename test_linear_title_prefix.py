import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5039",
            "title": "Hide default emissions section",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Hide default emissions section",
            },
        )

    def test_prefixes_nested_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5039",
                    "title": "Hide default emissions section",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["issueId"], "POI-5039")
        self.assertEqual(
            update["title"],
            "Cursor researching: Hide default emissions section",
        )

    def test_ignores_status_change_to_another_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-1",
            "title": "Keep unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger_even_when_status_matches(self):
        event = {
            "trigger": "comment_created",
            "status": "to research",
            "id": "POI-1",
            "title": "Keep unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "cursor researching: Keep unchanged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "TO_RESEARCH",
            "identifier": "POI-2",
            "title": "Normalize status",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status",
        )

    def test_prefixes_linear_update_when_updated_fields_include_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-3",
                "title": "Nested Linear update",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Nested Linear update",
            },
        )

    def test_prefixes_linear_update_from_changes_new_status(self):
        event = {
            "action": "Issue Updated",
            "data": {
                "identifier": "POI-4",
                "title": "Changed through changes",
                "changes": {
                    "workflowState": {
                        "old": {"name": "Backlog"},
                        "new": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed through changes",
        )

    def test_ignores_generic_issue_update_without_status_change_evidence(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-5",
                "title": "Description changed only",
                "status": "to research",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payload_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "No id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payload_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trim me",
        )

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "CLI smoke",
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
                "issueId": "POI-8",
                "title": "Cursor researching: CLI smoke",
            },
        )


if __name__ == "__main__":
    unittest.main()
