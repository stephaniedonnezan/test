import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4770",
                "title": "Cursor researching: Refactor IEmissionFactor",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_already_prefixed_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "cursor researching: Refactor IEmissionFactor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "issueId": "POI-4770",
                "title": "Refactor IEmissionFactor",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Refactor IEmissionFactor",
        )

    def test_uses_nested_linear_issue_for_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "webhook-event-id",
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "POI-4770",
                    "title": "Refactor IEmissionFactor",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Refactor IEmissionFactor",
            },
        )

    def test_accepts_update_metadata_split_across_nested_payload(self):
        event = {
            "action": "update",
            "data": {
                "updatedFields": ["workflowState"],
                "issue": {
                    "identifier": "POI-4770",
                    "title": "Refactor IEmissionFactor",
                    "workflowState": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4770",
                "title": "Cursor researching: Refactor IEmissionFactor",
            },
        )

    def test_requires_updated_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Refactor IEmissionFactor",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_stale_nested_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Refactor IEmissionFactor",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
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
                "issueId": "POI-4770",
                "title": "Cursor researching: Refactor IEmissionFactor",
            },
        )


if __name__ == "__main__":
    unittest.main()
