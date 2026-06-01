import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_flat_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: Methane closing warnings are merging",
            },
        )

    def test_builds_update_for_nested_trigger_context(self):
        result = build_issue_title_update(
            {
                "automationId": "automation-1",
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4588",
                    "title": "Nested issue title",
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_builds_update_for_linear_issue_updated_payload(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": [{"name": "Workflow State"}],
                "data": {
                    "issue": {
                        "id": "linear-issue-id",
                        "identifier": "POI-4588",
                        "title": "Webhook issue title",
                        "state": {"name": "to-research"},
                    }
                },
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Webhook issue title",
            },
        )

    def test_matches_status_and_trigger_variants(self):
        result = build_issue_title_update(
            {
                "action": "statusChanged",
                "new_status": "to_research",
                "issue_id": "POI-4588",
                "title": "Variant issue title",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Variant issue title")

    def test_ignores_status_changes_to_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4588",
                "title": "Issue title",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_events(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4588",
                "title": "Issue title",
            }
        )

        self.assertIsNone(result)

    def test_ignores_issue_updated_without_status_field_change(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description"],
                "status": "to research",
                "id": "POI-4588",
                "title": "Issue title",
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to-research",
                "id": "POI-4588",
                "title": f"{TITLE_PREFIX}: Issue title",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-4588"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Title"}
            )
        )

    def test_handler_alias_matches_primary_function(self):
        event = {
            "trigger": "stateChanged",
            "status": "to research",
            "identifier": "POI-4588",
            "title": "Alias title",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_json(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4588",
            "title": "CLI title",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
