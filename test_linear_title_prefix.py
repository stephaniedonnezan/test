import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4248",
            "title": "Expose an internal API",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4248",
                "title": "Cursor researching: Expose an internal API",
            },
        )

    def test_builds_update_for_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4248",
                "title": "Expose an internal API",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4248",
                "title": "Cursor researching: Expose an internal API",
            },
        )

    def test_builds_update_for_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4248",
                    "title": "Expose an internal API",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4248",
                "title": "Cursor researching: Expose an internal API",
            },
        )

    def test_accepts_status_name_variants(self):
        event = {
            "webhookType": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4248",
            "title": "Expose an internal API",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Expose an internal API",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4248",
            "title": "Expose an internal API",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-4248",
            "title": "Expose an internal API",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_are_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4248",
            "title": "cursor researching: Expose an internal API",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Expose an internal API",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_update_action(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-4248",
            "title": "Expose an internal API",
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
                "issueId": "POI-4248",
                "title": "Cursor researching: Expose an internal API",
            },
        )


if __name__ == "__main__":
    unittest.main()
