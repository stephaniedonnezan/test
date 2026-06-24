import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixed_update_for_cursor_trigger_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to research",
                    "id": "POI-4076",
                    "title": "Fix failing Cypress tests on main",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4076",
                "title": "Fix failing Cypress tests on main",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4076",
                "title": "Fix failing Cypress tests on main",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4076",
                "title": "cursor researching: Fix failing Cypress tests on main",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "ToResearch",
                "identifier": "POI-4076",
                "title": "Fix failing Cypress tests on main",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_handles_nested_linear_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4076",
                    "title": "Fix failing Cypress tests on main",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_generic_update_requires_status_field_metadata(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4076",
                    "title": "Fix failing Cypress tests on main",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_changed_status_destination(self):
        event = {
            "action": "update",
            "changes": {
                "workflowState": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "To Research"},
                }
            },
            "issue": {
                "identifier": "POI-4076",
                "title": "Fix failing Cypress tests on main",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "  POI-4076  ",
                "title": "  Fix failing Cypress tests on main  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )

    def test_missing_issue_id_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Fix failing Cypress tests on main",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_title_returns_none(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4076",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_mapping_event_returns_none(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4076",
                "title": "Fix failing Cypress tests on main",
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
                "issueId": "POI-4076",
                "title": "Cursor researching: Fix failing Cypress tests on main",
            },
        )


if __name__ == "__main__":
    unittest.main()
