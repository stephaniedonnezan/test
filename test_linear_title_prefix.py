import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2309",
            "title": "The Co2 emissions units are hardcoded",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2309",
                "title": "Cursor researching: The Co2 emissions units are hardcoded",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-2309",
                "title": "Investigate methane emissions",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2309",
                "title": "Cursor researching: Investigate methane emissions",
            },
        )

    def test_accepts_linear_issue_updated_payload_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-2309",
                "title": "Research display units",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research display units",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-2309",
            "title": "The Co2 emissions units are hardcoded",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Research display units",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2309",
            "title": "cursor researching: The Co2 emissions units are hardcoded",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_for_valid_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "id": "POI-2309",
            "title": "Fix emissions units",
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
                "issueId": "POI-2309",
                "title": "Cursor researching: Fix emissions units",
            },
        )


if __name__ == "__main__":
    unittest.main()
