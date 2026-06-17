import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


ISSUE_ID = "POI-3329"
ISSUE_TITLE = "Improve error messages when deliveries are not issuable"
PREFIXED_TITLE = f"Cursor researching: {ISSUE_TITLE}"


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": ISSUE_ID,
                "title": PREFIXED_TITLE,
            },
        )

    def test_uses_nested_trigger_context_from_automation_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": ISSUE_ID,
                "title": ISSUE_TITLE,
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": ISSUE_ID,
                "title": PREFIXED_TITLE,
            },
        )

    def test_accepts_nested_issue_payload(self):
        event = {
            "type": "statusChanged",
            "new_status": "to-research",
            "data": {
                "issue": {
                    "identifier": ISSUE_ID,
                    "title": ISSUE_TITLE,
                },
            },
        }

        self.assertEqual(build_issue_title_update(event)["title"], PREFIXED_TITLE)

    def test_accepts_issue_updated_when_status_field_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "state": {"name": "To Research"},
            "identifier": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertEqual(build_issue_title_update(event)["title"], PREFIXED_TITLE)

    def test_accepts_changed_status_values(self):
        event = {
            "action": "update",
            "changes": {"workflowState": {"newValue": {"name": "to research"}}},
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertEqual(build_issue_title_update(event)["title"], PREFIXED_TITLE)

    def test_accepts_mapping_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "workflowState": {"name": "To Research"},
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertEqual(build_issue_title_update(event)["title"], PREFIXED_TITLE)

    def test_skips_issue_updated_when_status_field_was_not_changed(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_current_todo_status(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": ISSUE_ID,
                "title": ISSUE_TITLE,
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": ISSUE_ID,
            "title": f"cursor researching: {ISSUE_TITLE}",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": ISSUE_TITLE,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": ISSUE_ID,
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "issueId": ISSUE_ID,
            "title": ISSUE_TITLE,
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


class CliTest(unittest.TestCase):
    def test_prints_update_action_for_stdin_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": ISSUE_ID,
            "title": ISSUE_TITLE,
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
                "issueId": ISSUE_ID,
                "title": PREFIXED_TITLE,
            },
        )


if __name__ == "__main__":
    unittest.main()
