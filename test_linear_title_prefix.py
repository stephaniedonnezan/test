import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_cursor_status_change_to_research_gets_prefixed_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5110",
                "title": "01 - processingMode column + routing flag",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5110",
                "title": "Cursor researching: 01 - processingMode column + routing flag",
            },
        )

    def test_status_normalization_accepts_separators_and_case(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-1",
            "title": "Investigate request",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate request",
        )

    def test_non_matching_status_is_ignored(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-2",
            "title": "Implement feature",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_issue_update_is_ignored_even_if_current_status_matches(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "To Research",
            "id": "POI-3",
            "title": "Research this",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_state_update_is_supported(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_changes_payload_new_status_is_supported(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "id": "POI-5",
            "title": "Changed issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed issue",
        )

    def test_existing_prefix_is_not_duplicated(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-6",
            "title": "cursor researching: Already tagged",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "title": "No id"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-7"}
            )
        )

    def test_wrapper_delegates_to_build_function(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-8",
            "title": "Delegate",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-9",
            "title": "CLI issue",
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
                "issueId": "POI-9",
                "title": "Cursor researching: CLI issue",
            },
        )


if __name__ == "__main__":
    unittest.main()
