import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5063",
                "title": "Improve performance of getPossibleQualifiedOutputItemsForLoadingEvent()",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5063",
                "title": "Cursor researching: Improve performance of getPossibleQualifiedOutputItemsForLoadingEvent()",
            },
        )

    def test_matches_status_case_and_separator_variations(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-1",
                "title": "Investigate loading event candidates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate loading event candidates",
        )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-2",
                "title": "Check possible qualified output items",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"state": {"name": "Todo"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Check possible qualified output items",
            },
        )

    def test_supports_linear_updated_from_state_id_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-11",
                "title": "State id changed",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "previous-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: State id changed",
        )

    def test_reads_new_status_from_change_object(self):
        event = {
            "webhookType": "issue",
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Research load qualification",
                }
            },
            "changes": {
                "state": {
                    "old": {"name": "Backlog"},
                    "new": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research load qualification",
        )

    def test_reads_new_status_from_change_list(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "identifier": "POI-4",
                "title": "Review loading candidates",
            },
            "updatedFields": [
                {"field": "workflowState", "newValue": {"name": "To Research"}}
            ],
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4",
        )

    def test_ignores_non_status_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "Do not prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-6",
                "title": "Do not prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "No issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "Cursor researching: Existing research task",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Existing research task",
        )

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "cursor researching - existing research task",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching - existing research task",
        )

    def test_returns_none_for_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-10",
                "title": "CLI title",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: CLI title",
            },
        )


if __name__ == "__main__":
    unittest.main()
