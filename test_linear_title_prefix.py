import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload_for_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4800",
            "title": "[]MB Grid Consumption zeros",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "issue_id": "POI-1",
            "title": "Carry meter values",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Carry meter values",
            },
        )

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Investigate report export",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate report export",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Duplicate",
            "id": "POI-4800",
            "title": "[]MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4800",
            "title": "[]MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_update_events_require_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4800",
            "title": "[]MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4800",
            "title": "cursor researching: []MB Grid Consumption zeros",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4800",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_cli_prints_update_action_as_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4800",
                "title": "[]MB Grid Consumption zeros",
            }
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
                "issueId": "POI-4800",
                "title": "Cursor researching: []MB Grid Consumption zeros",
            },
        )


if __name__ == "__main__":
    unittest.main()
