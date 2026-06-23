import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )

    def test_accepts_cursor_automation_trigger_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA POS should not be modifiable",
        )

    def test_accepts_camel_case_automation_trigger_wrapper(self):
        event = {
            "automationTriggerInfo": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                }
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5065")

    def test_accepts_status_with_camel_case_or_separators(self):
        for status in ("toResearch", "to-research", "to_research", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                }

                self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5065")

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5065",
            "title": "cursor researching: UBA POS should not be modifiable",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: UBA POS should not be modifiable",
        )

    def test_accepts_generic_issue_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-event-id",
                "issue": {
                    "identifier": "POI-5065",
                    "title": "UBA POS should not be modifiable",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5065")

    def test_accepts_linear_updated_from_state_id_marker(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFrom": {"stateId": "previous-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5065",
                "title": "UBA POS should not be modifiable",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA POS should not be modifiable",
        )

    def test_prefers_changed_status_over_stale_current_status(self):
        event = {
            "action": "update",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-5065",
                "title": "UBA POS should not be modifiable",
                "state": {"name": "Backlog"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5065")

    def test_ignores_generic_issue_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5065",
                "title": "UBA POS should not be modifiable",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5065",
            "title": "UBA POS should not be modifiable",
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
                "issueId": "POI-5065",
                "title": "Cursor researching: UBA POS should not be modifiable",
            },
        )


if __name__ == "__main__":
    unittest.main()
