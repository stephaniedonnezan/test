import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


ISSUE_TITLE = "MB export post QA updates"


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5093",
            "title": ISSUE_TITLE,
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_prefixes_title_for_cloud_automation_wrapper(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5093",
                    "title": ISSUE_TITLE,
                    "status": "To Research",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_accepts_camel_case_automation_wrapper_key(self):
        event = {
            "automationTriggerInfo": {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "issueId": "POI-5093",
                    "title": ISSUE_TITLE,
                }
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5093")

    def test_accepts_case_and_separator_variations(self):
        for status in ("toResearch", "to-research", "to_research", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "new_status": status,
                    "issueId": "POI-5093",
                    "title": ISSUE_TITLE,
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    f"Cursor researching: {ISSUE_TITLE}",
                )

    def test_skips_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "issueId": "POI-5093",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "issueId": "POI-5093",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_marked_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-5093",
            "title": f"cursor researching: {ISSUE_TITLE}",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "type": "Issue",
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-5093",
                    "title": ISSUE_TITLE,
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )

    def test_handles_linear_updated_from_state_id_marker(self):
        event = {
            "type": "Issue",
            "action": "update",
            "updatedFrom": {"stateId": "previous-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-5093",
                "title": ISSUE_TITLE,
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5093")

    def test_prefers_changed_status_over_stale_current_status(self):
        event = {
            "action": "update",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "identifier": "POI-5093",
                "title": ISSUE_TITLE,
                "state": {"name": "Backlog"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"Cursor researching: {ISSUE_TITLE}",
        )

    def test_generic_issue_update_requires_status_change_details(self):
        event = {
            "action": "update",
            "data": {
                "type": "Issue",
                "issue": {
                    "identifier": "POI-5093",
                    "title": ISSUE_TITLE,
                    "state": {"name": "To Research"},
                },
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
            "issueId": "POI-5093",
            "title": ISSUE_TITLE,
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": f"Cursor researching: {ISSUE_TITLE}",
            },
        )


if __name__ == "__main__":
    unittest.main()
