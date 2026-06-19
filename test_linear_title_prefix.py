import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove obsolete emissions inputs",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4637",
                "title": "cursor researching: Remove obsolete emissions inputs",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "identifier": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove obsolete emissions inputs",
            },
        )

    def test_handles_nested_linear_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4637",
                "title": "Remove obsolete emissions inputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove obsolete emissions inputs",
            },
        )

    def test_requires_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4637",
                "title": "Remove obsolete emissions inputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "workflowState": {
                    "old": {"name": "Todo"},
                    "new": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove obsolete emissions inputs",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Remove obsolete emissions inputs",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4637",
                "title": "Remove obsolete emissions inputs",
            },
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
                "issueId": "POI-4637",
                "title": "Cursor researching: Remove obsolete emissions inputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
