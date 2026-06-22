import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_status_change_to_research(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4932",
                "title": "Improve the delegate",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve the delegate",
            },
        )

    def test_nested_automation_trigger_context(self):
        action = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4932",
                        "title": "Stored file transaction delegate",
                    }
                }
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Stored file transaction delegate")

    def test_status_name_normalizes_separators_and_case(self):
        action = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "TO_RESEARCH",
                "issueId": "POI-4932",
                "title": "Stored files",
            }
        )

        self.assertIsNotNone(action)

    def test_generic_issue_update_uses_changed_status_target(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "data": {
                    "identifier": "POI-4932",
                    "title": "Stored files",
                    "changes": {"state": {"from": "Todo", "to": {"name": "To Research"}}},
                },
            }
        )

        self.assertEqual(action["issueId"], "POI-4932")
        self.assertEqual(action["title"], "Cursor researching: Stored files")

    def test_generic_issue_update_uses_current_state_when_status_field_changed(self):
        action = build_issue_title_update(
            {
                "action": "updated",
                "data": {
                    "id": "POI-4932",
                    "title": "Stored files",
                    "updatedFields": ["state"],
                    "state": {"name": "to-research"},
                },
            }
        )

        self.assertIsNotNone(action)

    def test_does_not_update_other_statuses(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4932",
                "title": "Improve the delegate",
            }
        )

        self.assertIsNone(action)

    def test_does_not_update_non_status_issue_update(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "data": {
                    "id": "POI-4932",
                    "title": "Improve the delegate",
                    "updatedFields": ["description"],
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_prefix(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4932",
                "title": "cursor researching: Improve the delegate",
            }
        )

        self.assertEqual(action["title"], "cursor researching: Improve the delegate")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4932",
                }
            )
        )

    def test_cli_outputs_action_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4932",
            "title": "Improve the delegate",
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
                "issueId": "POI-4932",
                "title": "Cursor researching: Improve the delegate",
            },
        )


if __name__ == "__main__":
    unittest.main()
