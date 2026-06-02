import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_status_changed_to_research_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4779",
            "title": "Downstream and transport emissions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4779",
                "title": "Cursor researching: Downstream and transport emissions",
            },
        )

    def test_accepts_nested_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4779",
                "title": "Downstream and transport emissions",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Downstream and transport emissions",
        )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": "POI-4779",
            "title": "Downstream and transport emissions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4779",
            "title": "Downstream and transport emissions",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4779",
            "title": "cursor researching: Downstream and transport emissions",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Downstream and transport emissions",
        )

    def test_accepts_linear_issue_update_payload_and_prefers_issue_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-4779",
                "title": "Downstream and transport emissions",
                "state": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4779",
                "title": "Cursor researching: Downstream and transport emissions",
            },
        )

    def test_ignores_issue_update_when_status_field_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4779",
                "title": "Downstream and transport emissions",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action_for_json_stdin(self):
        event = {
            "triggerContext": {
                "webhookType": "status_changed",
                "newStatus": "to research",
                "id": "POI-4779",
                "title": "Downstream and transport emissions",
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
                "issueId": "POI-4779",
                "title": "Cursor researching: Downstream and transport emissions",
            },
        )


if __name__ == "__main__":
    unittest.main()
