import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_flat_automation_payload(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4282",
                "title": "Edit GoO allocation in Energy Allocation Screen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4282",
                "title": "Cursor researching: Edit GoO allocation in Energy Allocation Screen",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4282",
                "title": "Edit GoO allocation in Energy Allocation Screen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4282",
                "title": "Edit GoO allocation in Energy Allocation Screen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4282",
                "title": "cursor researching: Edit GoO allocation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issue_id": "POI-4282",
            "title": "Edit GoO allocation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4282",
                "title": "Cursor researching: Edit GoO allocation",
            },
        )

    def test_supports_nested_linear_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "id": "POI-4282",
                "title": "Edit GoO allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4282",
                "title": "Cursor researching: Edit GoO allocation",
            },
        )

    def test_ignores_update_payload_when_status_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4282",
                "title": "Edit GoO allocation",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_nested_stale_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4282",
                "title": "Edit GoO allocation",
            },
            "data": {
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_action_when_update_is_needed(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4282",
                "title": "Edit GoO allocation",
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
                "issueId": "POI-4282",
                "title": "Cursor researching: Edit GoO allocation",
            },
        )


if __name__ == "__main__":
    unittest.main()
