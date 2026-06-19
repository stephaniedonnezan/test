import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_cloud_automation_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4280",
                    "title": "Duplicate id check",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_builds_title_update_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4280",
                "title": "Duplicate id check",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4280",
                "title": "Duplicate id check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4280",
                "title": "Duplicate id check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4280",
                "title": "cursor researching: Duplicate id check",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4280",
            "title": "Duplicate id check",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "id": "POI-4280",
                "title": "Duplicate id check",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_supports_linear_changes_payloads(self):
        event = {
            "action": "Issue Updated",
            "changes": {
                "state": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "identifier": "POI-4280",
                "title": "Duplicate id check",
                "state": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_ignores_update_payload_when_status_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4280",
                "title": "Duplicate id check",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_nested_stale_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4280",
                "title": "Duplicate id check",
            },
            "data": {
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-4280 ",
                "title": "  Duplicate id check  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )

    def test_cli_prints_action_when_update_is_needed(self):
        payload = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4280",
                    "title": "Duplicate id check",
                }
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4280",
                "title": "Cursor researching: Duplicate id check",
            },
        )


if __name__ == "__main__":
    unittest.main()
