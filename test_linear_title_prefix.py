import json
import subprocess
import sys
import unittest

from linear_issue_title import build_issue_title_update as compat_build_issue_title_update
from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_automation_status_change_to_research(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4730",
                "title": "Hide Add Input button in Container Allocation tab",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4730",
                "title": (
                    "Cursor researching: "
                    "Hide Add Input button in Container Allocation tab"
                ),
            },
        )

    def test_accepts_case_and_separator_variations_for_target_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "ToResearch",
            "id": "POI-4730",
            "title": "Investigate allocation inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4730",
                "title": "Cursor researching: Investigate allocation inputs",
            },
        )

    def test_accepts_linear_issue_update_when_state_field_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["stateId"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4730",
                "title": "Research allocation input controls",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research allocation input controls",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4730",
            "title": "Hide Add Input button in Container Allocation tab",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_issue_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Research allocation input controls",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4730",
            "title": "cursor researching - Investigate allocation inputs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title_and_issue_identifier_for_update_action(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": ""}
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

    def test_compatibility_module_exports_same_builder(self):
        event = {
            "newStatus": "to_research",
            "id": "POI-4730",
            "title": "Investigate allocation inputs",
        }

        self.assertEqual(
            compat_build_issue_title_update(event),
            build_issue_title_update(event),
        )


class UpdateIssueTitleForStatusTest(unittest.TestCase):
    def test_adds_prefix_for_to_research_status(self):
        self.assertEqual(
            update_issue_title_for_status("Investigate allocation inputs", "To Research"),
            "Cursor researching: Investigate allocation inputs",
        )

    def test_leaves_title_unchanged_for_other_status(self):
        self.assertEqual(
            update_issue_title_for_status("Investigate allocation inputs", "In Progress"),
            "Investigate allocation inputs",
        )

    def test_does_not_duplicate_existing_colon_prefix(self):
        self.assertEqual(
            update_issue_title_for_status(
                "Cursor researching: Investigate allocation inputs",
                "to research",
            ),
            "Cursor researching: Investigate allocation inputs",
        )


class DeriveUpdatedTitleTest(unittest.TestCase):
    def test_returns_updated_title_without_requiring_issue_id(self):
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "Investigate allocation inputs",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: Investigate allocation inputs",
        )

    def test_returns_none_when_no_title_update_is_needed(self):
        self.assertIsNone(
            derive_updated_title(
                {"triggerContext": {"newStatus": "QA", "title": "Issue title"}}
            )
        )
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


class CliTest(unittest.TestCase):
    def test_cli_prints_json_update_for_valid_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4730",
            "title": "Investigate allocation inputs",
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
                "issueId": "POI-4730",
                "title": "Cursor researching: Investigate allocation inputs",
            },
        )

    def test_cli_exits_nonzero_for_invalid_json(self):
        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input="{not-json",
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid JSON payload", result.stderr)


if __name__ == "__main__":
    unittest.main()
