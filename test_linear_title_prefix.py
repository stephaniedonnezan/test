import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
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

    def test_uses_status_when_new_status_is_not_present(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Create production site form",
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4811",
                "title": "cursor researching: Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Create production site form",
        )

    def test_reads_issue_details_from_nested_data(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4811",
                    "title": "Create production site form",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )

    def test_handles_linear_webhook_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "issue-uuid",
                "title": "Create production site form",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Create production site form",
            },
        )

    def test_requires_updated_status_field_for_generic_issue_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-uuid",
                "title": "Create production site form",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_explicit_new_status_wins_over_nested_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "data": {
                    "id": "POI-4811",
                    "title": "Create production site form",
                    "status": "Backlog",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Create production site form",
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "id": "POI-4811",
            "title": "Create production site form",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_returns_none_for_malformed_payloads(self):
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"}))
        self.assertIsNone(build_issue_title_update("not a mapping"))

    def test_cli_prints_json_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4811",
            "title": "Create production site form",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )


if __name__ == "__main__":
    unittest.main()
