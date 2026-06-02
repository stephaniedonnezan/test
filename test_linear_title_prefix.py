import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_trigger_context_status_changed_to_research(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4781",
                "title": 'Issue on delivery with "Prevent PoS Issuance" - 8713',
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4781",
                "title": 'Cursor researching: Issue on delivery with "Prevent PoS Issuance" - 8713',
            },
        )

    def test_accepts_camel_case_and_underscore_status_spellings(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4781",
            "title": "Research certificate generation",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research certificate generation",
        )

    def test_accepts_linear_issue_updated_payload_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4781",
                "title": "Research delivery PoS issuance",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research delivery PoS issuance",
            },
        )

    def test_accepts_workflow_state_changed_payload(self):
        event = {
            "action": "update",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "issue-uuid",
                "title": "Research PoS prevention lock",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research PoS prevention lock",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4781",
            "title": 'Issue on delivery with "Prevent PoS Issuance" - 8713',
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4781",
            "title": 'Issue on delivery with "Prevent PoS Issuance" - 8713',
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_issue_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Research delivery PoS issuance",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4781",
            "title": "cursor researching: Research delivery PoS issuance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4781",
            "title": "Research delivery PoS issuance",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_for_valid_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "ToResearch",
            "id": "POI-4781",
            "title": "Research delivery PoS issuance",
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
                "issueId": "POI-4781",
                "title": "Cursor researching: Research delivery PoS issuance",
            },
        )


if __name__ == "__main__":
    unittest.main()
