import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_payload(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4635",
                "title": "When ingested document is deleted, only title is deleted",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4635",
                "title": (
                    "Cursor researching: "
                    "When ingested document is deleted, only title is deleted"
                ),
            },
        )

    def test_accepts_cloud_automation_trigger_context_wrapper(self):
        result = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4635",
                        "title": "Document extraction row remains after deletion",
                    }
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-4635")
        self.assertEqual(
            result["title"],
            "Cursor researching: Document extraction row remains after deletion",
        )

    def test_accepts_status_name_variants(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-1",
                "title": "Research me",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Research me")

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4635",
                "title": "Already done",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_changed_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4635",
                "title": "Comment only",
            }
        )

        self.assertIsNone(result)

    def test_ignores_already_prefixed_titles(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4635",
                "title": "cursor researching: Existing title",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Missing id",
            }
        )

        self.assertIsNone(result)

    def test_requires_title(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4635",
            }
        )

        self.assertIsNone(result)

    def test_accepts_nested_linear_issue_payload(self):
        result = build_issue_title_update(
            {
                "webhookType": "status_changed",
                "newStatus": "to research",
                "data": {
                    "issue": {
                        "identifier": "POI-4635",
                        "title": "Nested Linear issue",
                    }
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-4635")
        self.assertEqual(result["title"], "Cursor researching: Nested Linear issue")

    def test_accepts_generic_update_when_updated_fields_include_status(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description", "workflowState"],
                "state": {"name": "To Research"},
                "id": "POI-4635",
                "title": "Generic update",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Generic update")

    def test_ignores_generic_update_without_status_field(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description"],
                "state": {"name": "To Research"},
                "id": "POI-4635",
                "title": "Description update",
            }
        )

        self.assertIsNone(result)

    def test_accepts_status_from_changes_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
                "id": "POI-4635",
                "title": "Changed status",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Changed status")

    def test_prefers_explicit_new_status_over_stale_issue_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "data": {
                    "issue": {
                        "id": "POI-4635",
                        "title": "Stale issue status",
                        "status": "To Research",
                    }
                },
            }
        )

        self.assertIsNone(result)

    def test_cli_prints_update_action(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4635",
                    "title": "CLI issue",
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4635",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
