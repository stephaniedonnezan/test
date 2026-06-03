import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_status_change_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4686",
                "title": "Cursor researching: Discuss with Stephanie",
            },
        )

    def test_ignores_current_canceled_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
                "status": "Canceled",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4686",
                "title": "cursor researching: Discuss with Stephanie",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_case_separators_and_camel_case(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": " POI-4686 ",
                "title": " Discuss with Stephanie ",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4686",
                "title": "Cursor researching: Discuss with Stephanie",
            },
        )

    def test_accepts_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-4686",
                    "title": "Discuss with Stephanie",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4686",
                "title": "Cursor researching: Discuss with Stephanie",
            },
        )

    def test_ignores_nested_issue_update_without_status_change_details(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["title"],
                "issue": {
                    "identifier": "POI-4686",
                    "title": "Discuss with Stephanie",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_current_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "status": "Canceled",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4686",
                "title": "Cursor researching: Discuss with Stephanie",
            },
        )

    def test_returns_none_for_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4686",
                "title": "Discuss with Stephanie",
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
                "issueId": "POI-4686",
                "title": "Cursor researching: Discuss with Stephanie",
            },
        )


if __name__ == "__main__":
    unittest.main()
