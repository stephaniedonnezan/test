import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_automation_trigger_context_when_new_status_is_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: [FE]Refine the dialog(s) in the Meters Page",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3626",
                "title": "[FE]Refine the dialog(s) in the Meters Page",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-3626",
                "title": "cursor researching: [FE]Refine dialogs",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_variant_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "issueId": "POI-3626",
            "title": "Refine dialogs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: Refine dialogs",
            },
        )

    def test_accepts_nested_linear_issue_update_with_changed_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-3626",
                "title": "Refine dialogs",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Refine dialogs",
            },
        )

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-3626",
                "title": "Refine dialogs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_updated_fields_status_marker(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "id": "POI-3626",
                "title": "Refine dialogs",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: Refine dialogs",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "new_status": "To Research",
            "issue_id": "  POI-3626  ",
            "title": "  Refine dialogs  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3626",
                "title": "Cursor researching: Refine dialogs",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-3626"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "Refine"}
            )
        )

    def test_cli_prints_compact_update_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3626",
            "title": "Refine dialogs",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            result.stdout.strip(),
            '{"action":"update_issue_title","issueId":"POI-3626","title":"Cursor researching: Refine dialogs"}',
        )


if __name__ == "__main__":
    unittest.main()
