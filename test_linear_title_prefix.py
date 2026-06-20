import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_event_entering_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": "Cursor researching: Loading message goes behind Mass Balance items",
            },
        )

    def test_supports_cursor_cloud_automation_trigger_context(self):
        update = build_issue_title_update(
            {
                "automation_trigger_info": {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-123",
                        "title": "Investigate transfer matching",
                    }
                }
            }
        )

        self.assertEqual(update["issueId"], "POI-123")
        self.assertEqual(update["title"], "Cursor researching: Investigate transfer matching")

    def test_ignores_status_changes_to_other_statuses(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_trigger_even_with_target_status_value(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        )

        self.assertIsNone(update)

    def test_skips_titles_that_already_have_prefix_case_insensitively(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "newStatus": "to research",
                "id": "POI-456",
                "title": "cursor researching: Existing research title",
            }
        )

        self.assertIsNone(update)

    def test_normalizes_status_and_trigger_separators(self):
        update = build_issue_title_update(
            {
                "trigger": "stateChanged",
                "new_status": "to_research",
                "identifier": "POI-789",
                "title": "Normalize status names",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Normalize status names")

    def test_supports_generic_issue_update_when_state_field_changed(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "identifier": "POI-321",
                    "title": "Research workflow transition",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-321")
        self.assertEqual(update["title"], "Cursor researching: Research workflow transition")

    def test_ignores_generic_update_without_status_field_change(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "data": {
                    "identifier": "POI-321",
                    "title": "Research workflow transition",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(update)

    def test_supports_nested_linear_changes_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "type": "Issue",
                "changes": {"status": {"from": "Backlog", "to": "To Research"}},
                "data": {
                    "issue": {
                        "identifier": "POI-654",
                        "id": "linear-uuid",
                        "title": "Nested issue payload",
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-654")
        self.assertEqual(update["title"], "Cursor researching: Nested issue payload")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                }
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

    def test_trims_issue_id_and_title(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-777 ",
                "title": "  Trimmed title  ",
            }
        )

        self.assertEqual(update["issueId"], "POI-777")
        self.assertEqual(update["title"], "Cursor researching: Trimmed title")

    def test_cli_prints_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-999",
            "title": "CLI smoke test",
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
                "issueId": "POI-999",
                "title": "Cursor researching: CLI smoke test",
            },
        )


if __name__ == "__main__":
    unittest.main()
