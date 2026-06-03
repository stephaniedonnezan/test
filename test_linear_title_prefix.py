import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4799",
                "title": "No May events when exporting",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4799",
                "title": "Cursor researching: No May events when exporting",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4799",
                "title": "No May events when exporting",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4799",
                "title": "No May events when exporting",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "issueId": "POI-4799",
            "title": "cursor researching: No May events when exporting",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_camel_case_status_and_trigger(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4799",
            "title": "No May events when exporting",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: No May events when exporting",
        )

    def test_reads_issue_details_from_nested_data(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4799",
                    "title": "No May events when exporting",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4799",
                "title": "Cursor researching: No May events when exporting",
            },
        )

    def test_handles_linear_webhook_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "id": "linear-issue-uuid",
                "title": "No May events when exporting",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-uuid",
                "title": "Cursor researching: No May events when exporting",
            },
        )

    def test_handles_updated_fields_as_field_objects(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": [{"name": "Workflow State"}],
            "status": "to-research",
            "issueId": "POI-4799",
            "title": "No May events when exporting",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: No May events when exporting",
        )

    def test_ignores_issue_updated_without_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description"],
            "status": "to research",
            "issueId": "POI-4799",
            "title": "No May events when exporting",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_explicit_new_status_wins_over_nested_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "data": {
                    "id": "POI-4799",
                    "title": "No May events when exporting",
                    "status": "Backlog",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: No May events when exporting",
        )

    def test_alias_matches_primary_handler(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4799",
            "title": "No May events when exporting",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_json_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4799",
            "title": "No May events when exporting",
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
                "issueId": "POI-4799",
                "title": "Cursor researching: No May events when exporting",
            },
        )


if __name__ == "__main__":
    unittest.main()
