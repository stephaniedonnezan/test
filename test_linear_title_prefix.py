import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4725",
                "title": "UX Design of delivery chains",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4725",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4725",
            "title": "UX Design of delivery chains",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4725",
            "title": "UX Design of delivery chains",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4725",
            "title": "cursor researching: UX Design of delivery chains",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4725",
                "title": "UX Design of delivery chains",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )

    def test_handles_workflow_state_update_metadata(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": {"workflowState": "old-state-id"},
            "data": {
                "identifier": "POI-4725",
                "title": "UX Design of delivery chains",
                "workflowState": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4725",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "id": " POI-4725 ",
            "title": " UX Design of delivery chains ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4725",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4725",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4725",
            "title": "UX Design of delivery chains",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            capture_output=True,
            check=True,
            encoding="utf-8",
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4725",
                "title": "Cursor researching: UX Design of delivery chains",
            },
        )


if __name__ == "__main__":
    unittest.main()
