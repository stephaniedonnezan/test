import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5101",
                "title": "Deploy infrastructure from a feature branch",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5101",
                "title": "Cursor researching: Deploy infrastructure from a feature branch",
            },
        )

    def test_builds_update_for_nested_automation_trigger_info(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5101",
                    "title": "  Research branch deploys  ",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5101",
                "title": "Cursor researching: Research branch deploys",
            },
        )

    def test_accepts_status_trigger_and_current_status_fallback(self):
        event = {
            "webhookType": "statusChanged",
            "status": "to_research",
            "issueId": "POI-5101",
            "title": "Feature branch infrastructure",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5101",
                "title": "Cursor researching: Feature branch infrastructure",
            },
        )

    def test_accepts_generic_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-5101",
                    "title": "Google auth for feature deploys",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5101",
                "title": "Cursor researching: Google auth for feature deploys",
            },
        )

    def test_changes_take_precedence_over_stale_issue_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "id": "POI-5101",
                    "title": "Automated infrastructure deployments",
                    "status": "In Progress",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5101",
                "title": "Cursor researching: Automated infrastructure deployments",
            },
        )

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5101",
            "title": "Deploy infrastructure from a feature branch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-5101",
            "title": "Deploy infrastructure from a feature branch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5101",
            "title": "Deploy infrastructure from a feature branch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_when_changes_move_to_other_status(self):
        event = {
            "action": "update",
            "changes": {"state": {"to": {"name": "Done"}}},
            "data": {
                "issue": {
                    "identifier": "POI-5101",
                    "title": "Deploy infrastructure from a feature branch",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5101",
            "title": "cursor researching: Deploy infrastructure from a feature branch",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_or_incomplete_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5101",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-5101",
            "title": "Deploy infrastructure from a feature branch",
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
                "issueId": "POI-5101",
                "title": "Cursor researching: Deploy infrastructure from a feature branch",
            },
        )


if __name__ == "__main__":
    unittest.main()
