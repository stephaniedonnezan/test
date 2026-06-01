import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_status_changed_to_research_builds_title_update(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4404",
                "title": "REST API controllers for document extraction",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4404",
                "title": "Cursor researching: REST API controllers for document extraction",
            },
        )

    def test_automation_trigger_context_payload_is_supported(self):
        update = build_issue_title_update(
            {
                "automationId": "automation-id",
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Design extraction schema",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-123")
        self.assertEqual(update["title"], "Cursor researching: Design extraction schema")

    def test_status_normalization_accepts_camel_case_and_separators(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-124",
                "title": "Classify uploaded files",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Classify uploaded files")

    def test_ignores_status_changes_to_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4404",
                "title": "REST API controllers for document extraction",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_triggers(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4404",
                "title": "REST API controllers for document extraction",
            }
        )

        self.assertIsNone(update)

    def test_ignores_titles_that_already_have_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4404",
                "title": "cursor researching: REST API controllers for document extraction",
            }
        )

        self.assertIsNone(update)

    def test_nested_linear_issue_update_with_status_field_is_supported(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "issue-uuid",
                        "identifier": "POI-125",
                        "title": "Extract biomethane documents",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "issue-uuid")
        self.assertEqual(
            update["title"], "Cursor researching: Extract biomethane documents"
        )

    def test_linear_update_without_status_field_is_ignored(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "issue": {
                        "id": "POI-126",
                        "title": "Extract biomethane documents",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertIsNone(update)

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-127",
            "title": "Generate API client",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-127",
                "title": "Cursor researching: Generate API client",
            },
        )


if __name__ == "__main__":
    unittest.main()
