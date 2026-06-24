import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4455",
            "title": "Clean up ProductionSiteQualifiedOutputModule",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_prefixes_title_for_cursor_automation_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4455",
                    "title": "Clean up ProductionSiteQualifiedOutputModule",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Blocked",
            "id": "POI-4455",
            "title": "Clean up ProductionSiteQualifiedOutputModule",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4455",
            "title": "Clean up ProductionSiteQualifiedOutputModule",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4455",
            "title": "cursor researching: Clean up ProductionSiteQualifiedOutputModule",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "Status Changed",
            "new_status": "TO-RESEARCH",
            "issue_id": "POI-4455",
            "title": " Clean up ProductionSiteQualifiedOutputModule ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_accepts_generic_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "identifier": "POI-4455",
                "title": "Clean up ProductionSiteQualifiedOutputModule",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_ignores_generic_issue_update_for_non_status_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4455",
                "title": "Clean up ProductionSiteQualifiedOutputModule",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issueId": "POI-4455",
            "title": "Clean up ProductionSiteQualifiedOutputModule",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_returns_none_without_issue_id_or_title(self):
        event = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4455",
            "title": "Clean up ProductionSiteQualifiedOutputModule",
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
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )


if __name__ == "__main__":
    unittest.main()
