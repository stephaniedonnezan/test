import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2598",
                "title": "Cursor researching: Site management deliveries table",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2598",
                "title": "cursor researching: Site management deliveries table",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To-Research",
                "id": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: Site management deliveries table")

    def test_uses_status_fallback_for_direct_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to_research",
                "identifier": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-2598")

    def test_builds_update_for_nested_linear_status_update(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-2598",
                    "title": "Site management deliveries table",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2598",
                "title": "Cursor researching: Site management deliveries table",
            },
        )

    def test_builds_update_when_changes_contains_status_field(self):
        event = {
            "action": "updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-2598",
                    "title": "Site management deliveries table",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-2598")

    def test_ignores_generic_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-2598",
                    "title": "Site management deliveries table",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-2598 ",
                "title": "  Site management deliveries table  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2598",
                "title": "Cursor researching: Site management deliveries table",
            },
        )

    def test_ignores_invalid_or_incomplete_payloads(self):
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(build_issue_title_update({"triggerContext": "bad"}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-2598",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2598",
                "title": "Site management deliveries table",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-2598",
                "title": "Cursor researching: Site management deliveries table",
            },
        )


if __name__ == "__main__":
    unittest.main()
