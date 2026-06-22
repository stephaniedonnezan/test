import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5090",
                "title": "Add Input draft toggle",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add Input draft toggle",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Triage",
                "id": "POI-5090",
                "title": "Add Input draft toggle",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5090",
                "title": "Add Input draft toggle",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5090",
                "title": "Add Input draft toggle",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants_for_research_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-5090",
            "title": "Add Input draft toggle",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add Input draft toggle",
        )

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5090",
            "title": "cursor researching: Add Input draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5090",
                "title": "Add Input draft toggle",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5090",
                "title": "Cursor researching: Add Input draft toggle",
            },
        )

    def test_uses_nested_issue_object(self):
        event = {
            "webhookType": "status_changed",
            "data": {
                "issue": {
                    "identifier": "POI-5090",
                    "title": "Add Input draft toggle",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-5090",
        )

    def test_reads_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"state": {"to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-5090",
                "title": "Add Input draft toggle",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add Input draft toggle",
        )

    def test_missing_issue_id_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Add Input draft toggle",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5090",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5090",
            "title": "Add Input draft toggle",
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
                "issueId": "POI-5090",
                "title": "Cursor researching: Add Input draft toggle",
            },
        )


if __name__ == "__main__":
    unittest.main()
