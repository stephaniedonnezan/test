import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5072",
                "title": "Add first updated manual to codebase",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-5072",
                "title": "Cursor researching: Add first updated manual to codebase",
            },
        )

    def test_cursor_automation_trigger_context_payload(self):
        update = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "triggerType": "linear",
                        "webhookType": "issue",
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-5072",
                        "title": "Add first updated manual to codebase",
                    }
                }
            }
        )

        self.assertEqual(update["issueId"], "POI-5072")
        self.assertEqual(
            update["title"],
            "Cursor researching: Add first updated manual to codebase",
        )

    def test_ignores_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-5072",
                "title": "Add first updated manual to codebase",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_triggers(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5072",
                "title": "Add first updated manual to codebase",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-5072",
                "title": "cursor researching: Add first updated manual to codebase",
            }
        )

        self.assertEqual(
            update["title"],
            "cursor researching: Add first updated manual to codebase",
        )

    def test_normalizes_status_and_trigger_separators(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issue_id": "POI-5072",
                "title": "Add first updated manual to codebase",
            }
        )

        self.assertEqual(update["issueId"], "POI-5072")

    def test_nested_linear_issue_update_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-5072",
                        "title": "Add first updated manual to codebase",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-5072",
                "title": "Cursor researching: Add first updated manual to codebase",
            },
        )

    def test_generic_update_requires_status_changed_field(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["priority"],
                "data": {
                    "issue": {
                        "identifier": "POI-5072",
                        "title": "Add first updated manual to codebase",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(update)

    def test_reads_new_status_from_changes_object(self):
        update = build_issue_title_update(
            {
                "type": "Issue Updated",
                "changes": {"workflowState": {"new": {"name": "To Research"}}},
                "issue": {
                    "identifier": "POI-5072",
                    "title": "Add first updated manual to codebase",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-5072")
        self.assertEqual(
            update["title"],
            "Cursor researching: Add first updated manual to codebase",
        )

    def test_trims_issue_id_and_title(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-5072 ",
                "title": " Add first updated manual to codebase ",
            }
        )

        self.assertEqual(update["issueId"], "POI-5072")
        self.assertEqual(
            update["title"],
            "Cursor researching: Add first updated manual to codebase",
        )

    def test_missing_issue_identity_or_title_is_noop(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Add first updated manual to codebase",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5072",
                }
            )
        )

    def test_non_mapping_payload_is_noop(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_update_action_for_stdin_json(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5072",
                    "title": "Add first updated manual to codebase",
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5072",
                "title": "Cursor researching: Add first updated manual to codebase",
            },
        )


if __name__ == "__main__":
    unittest.main()
