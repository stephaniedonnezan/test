import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_automation_status_changed_payload_for_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
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

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-2",
                "title": "Investigate report export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate report export",
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Cross border PPA",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Cross border PPA",
            },
        )

    def test_supports_nested_trigger_context_issue_payloads(self):
        event = {
            "triggerContext": {
                "trigger": "workflowStateChanged",
                "issue": {
                    "identifier": "POI-3",
                    "title": "Review site config",
                    "workflowState": {"name": "To Research"},
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Review site config",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4",
            "title": "Comment-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_update_events_require_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-5",
            "title": "Description-only update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
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
                "id": "POI-4811",
                "title": "Create production site form",
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
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )


if __name__ == "__main__":
    unittest.main()
