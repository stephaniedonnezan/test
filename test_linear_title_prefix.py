import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_cursor_trigger_context_status_changed_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4252",
                "title": "Better strategy in the mapAllRows to choose the mapper",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4252",
                "title": "Cursor researching: Better strategy in the mapAllRows to choose the mapper",
            },
        )

    def test_flat_status_changed_payload(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To Research",
            "issueId": "POI-1",
            "title": "Research me",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research me",
            },
        )

    def test_normalizes_target_status_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch", " To Research "):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "issueId": "POI-2",
                    "title": "Normalize status",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Normalize status",
                )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "issueId": "POI-3",
            "title": "Already complete",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "issueId": "POI-4",
            "title": "Do not rename",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-5",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-6",
            "title": "  Trim me  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trim me",
        )

    def test_nested_linear_update_with_state_field(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-7",
                "title": "Nested payload",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-7",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_nested_issue_payload_under_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "workflowStateChanged",
                "data": {
                    "issue": {
                        "identifier": "POI-8",
                        "title": "Nested issue",
                        "workflowState": {"name": "To Research"},
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Nested issue",
        )

    def test_generic_update_requires_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-9",
                "title": "Unrelated update",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_changes_object_can_supply_new_status(self):
        event = {
            "action": "issue.updated",
            "changes": {"status": {"from": "Todo", "to": {"name": "To Research"}}},
            "data": {"identifier": "POI-10", "title": "Changed status"},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed status",
        )

    def test_missing_issue_id_or_title_returns_none(self):
        valid_status_change = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update({**valid_status_change, "title": "No id"}))
        self.assertIsNone(build_issue_title_update({**valid_status_change, "issueId": "POI-11"}))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-12",
                "title": "CLI payload",
            }
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
                "issueId": "POI-12",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
