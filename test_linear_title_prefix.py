import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_automation_trigger_context_for_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4789",
                "title": "PoS auto reporting to official databases",
                "status": "To Research",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4789",
                "title": "Cursor researching: PoS auto reporting to official databases",
            },
        )

    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4789",
            "title": "PoS auto reporting to official databases",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4789",
                "title": "Cursor researching: PoS auto reporting to official databases",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4789",
                "title": "PoS auto reporting to official databases",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4789",
                "title": "Cursor researching: PoS auto reporting to official databases",
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4789",
            "title": "PoS auto reporting to official databases",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4789",
            "title": "PoS auto reporting to official databases",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4789",
            "title": "PoS auto reporting to official databases",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4789",
                "title": "PoS auto reporting to official databases",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4789",
            "title": "cursor researching: PoS auto reporting to official databases",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4789",
                "title": "PoS auto reporting to official databases",
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
                "issueId": "POI-4789",
                "title": "Cursor researching: PoS auto reporting to official databases",
            },
        )


if __name__ == "__main__":
    unittest.main()
