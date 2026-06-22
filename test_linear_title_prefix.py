import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use",
            },
        )

    def test_prefixes_cursor_automation_trigger_context(self):
        update = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "triggerType": "linear",
                        "webhookType": "issue",
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-5050",
                        "title": "Investigate certification flow",
                    }
                }
            }
        )

        self.assertEqual(update["issueId"], "POI-5050")
        self.assertEqual(update["title"], "Cursor researching: Investigate certification flow")

    def test_uses_status_fallback_when_new_status_is_absent(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "status": "to_research",
                    "id": "POI-5050",
                    "title": "Research fallback status",
                }
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Research fallback status")

    def test_ignores_status_changes_to_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_triggers(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        )

        self.assertIsNone(update)

    def test_ignores_generic_updates_without_status_metadata(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "status": "to research",
                "id": "POI-5050",
                "title": "Bug: compliant co2 mixed e_ex_use",
            }
        )

        self.assertIsNone(update)

    def test_skips_titles_that_already_have_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5050",
                "title": "cursor researching: Bug: compliant co2 mixed e_ex_use",
            }
        )

        self.assertIsNone(update)

    def test_accepts_camel_case_target_status(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-5050",
                "title": "Camel case status",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Camel case status")

    def test_accepts_nested_linear_issue_update_with_updated_fields(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-5050",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-5050",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_accepts_status_from_change_map(self):
        update = build_issue_title_update(
            {
                "action": "Issue Updated",
                "changes": {"status": {"from": "Backlog", "to": "To Research"}},
                "data": {
                    "issue": {
                        "identifier": "POI-5050",
                        "title": "Change map status",
                    }
                },
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Change map status")

    def test_requires_issue_id(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "No issue id",
            }
        )

        self.assertIsNone(update)

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5050",
            "title": "CLI payload",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(json.loads(result.stdout)["title"], "Cursor researching: CLI payload")


if __name__ == "__main__":
    unittest.main()
