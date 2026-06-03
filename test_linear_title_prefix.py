import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4744",
            "title": "Skip transport emissions is failing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4744",
                "title": "Cursor researching: Skip transport emissions is failing",
            },
        )

    def test_prefixes_nested_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4744",
                "title": "Skip transport emissions is failing",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4744",
                "title": "Cursor researching: Skip transport emissions is failing",
            },
        )

    def test_ignores_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4744",
            "title": "Skip transport emissions is failing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4744",
            "title": "Skip transport emissions is failing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_casing_and_separators(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-4744",
            "title": "Skip transport emissions is failing",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Skip transport emissions is failing",
        )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to_research",
            "identifier": "POI-4744",
            "title": "Skip transport emissions is failing",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4744")

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4744",
                    "title": "Skip transport emissions is failing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4744",
                "title": "Cursor researching: Skip transport emissions is failing",
            },
        )

    def test_supports_workflow_state_payloads(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["workflowState"],
            "issue": {
                "id": "issue-uuid",
                "title": "Skip transport emissions is failing",
                "workflowState": {"name": "toResearch"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "issue-uuid")

    def test_supports_updated_from_state_id_on_linear_updates(self):
        event = {
            "type": "Issue Updated",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "title": "Skip transport emissions is failing",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "issue-uuid")

    def test_ignores_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4744",
                    "title": "Skip transport emissions is failing",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_research_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4744",
            "title": "cursor researching: Skip transport emissions is failing",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-4744"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))

    def test_cli_prints_computed_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4744",
            "title": "Skip transport emissions is failing",
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
                "issueId": "POI-4744",
                "title": "Cursor researching: Skip transport emissions is failing",
            },
        )


if __name__ == "__main__":
    unittest.main()
