import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4803",
            "title": "Users should be able to close a delivery",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4803",
                "title": "Cursor researching: Users should be able to close a delivery",
            },
        )

    def test_accepts_automation_trigger_context_shape(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-4803",
                "title": "Investigate emissions calculation",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4803",
                "title": "Cursor researching: Investigate emissions calculation",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4810",
                "title": "Nested payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4810",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_supports_camel_case_status_changed_marker(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "issueId": "POI-4811",
            "title": "Camel case trigger",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4811",
                "title": "Cursor researching: Camel case trigger",
            },
        )

    def test_returns_none_for_different_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Duplicate",
            "id": "POI-4803",
            "title": "Not a research issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-4803",
            "title": "Title-only update",
            "status": "To Research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_has_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4803",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_required_issue_fields_are_missing(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4803",
            "title": "CLI event",
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
                "issueId": "POI-4803",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
