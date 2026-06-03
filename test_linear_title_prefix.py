import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_trigger_context(self):
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

    def test_matches_status_and_trigger_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "issueId": "POI-1",
                "title": "Investigate calculation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate calculation",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
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

    def test_ignores_already_prefixed_titles(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "cursor researching: Refactor IEmissionFactor",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4770",
                "title": "Refactor IEmissionFactor",
                "state": {"name": "To Research"},
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

    def test_handles_status_change_target_names(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "issue": {
                "issue_id": "POI-2",
                "title": "Research issue",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research issue",
            },
        )

    def test_requires_status_field_for_generic_issue_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4770",
                "title": "Refactor IEmissionFactor",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_stale_nested_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            },
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Refactor IEmissionFactor",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4770",
                    }
                }
            )
        )

        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Missing id",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4770",
                "title": "Refactor IEmissionFactor",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4770",
                "title": "Cursor researching: Refactor IEmissionFactor",
            },
        )


if __name__ == "__main__":
    unittest.main()
