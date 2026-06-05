import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4817",
            "title": "User must be able to add an input",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4817",
                "title": "Cursor researching: User must be able to add an input",
            },
        )

    def test_accepts_wrapped_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4817",
                "title": "Wrapped issue",
            }
        }

        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4817",
                "title": "Cursor researching: Wrapped issue",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("ToResearch", "to-research", "to_research", " TO   RESEARCH "):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-1",
                    "title": "Normalize me",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Normalize me",
                )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "DEV",
            "id": "POI-4817",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4817",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4817",
            "title": " cursor RESEARCHING: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-1"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Missing id"}
            )
        )

    def test_accepts_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4817",
                    "title": "Nested issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4817",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_accepts_changes_mapping_new_status(self):
        event = {
            "action": "update",
            "data": {"issue": {"id": "lin_123", "title": "Changed issue"}},
            "changes": {"state": {"from": {"name": "Backlog"}, "to": {"name": "To Research"}}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed issue",
        )

    def test_accepts_changes_list_new_status(self):
        event = {
            "action": "issue updated",
            "data": {"issue": {"identifier": "POI-2", "title": "Changed by list"}},
            "changes": [
                {"field": "priority", "newValue": "High"},
                {"field": "workflowState", "newValue": {"name": "to research"}},
            ],
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed by list",
        )

    def test_uses_current_issue_state_when_updated_from_only_has_old_status(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "Backlog"}},
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Updated from old state",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Updated from old state",
        )

    def test_does_not_treat_old_status_as_new_status(self):
        event = {
            "action": "update",
            "updatedFrom": {"state": {"name": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Moved away",
                    "state": {"name": "DEV"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_workflow_state_name(self):
        event = {
            "action": "update",
            "updatedFields": ["workflowState"],
            "issue": {
                "identifier": "POI-5",
                "title": "Workflow issue",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Workflow issue",
        )

    def test_rejects_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_or_null(self):
        positive = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-CLI",
            "title": "CLI issue",
        }
        positive_run = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(positive),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(positive_run.stdout)["title"], "Cursor researching: CLI issue")

        negative = dict(positive, newStatus="DEV")
        negative_run = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(negative),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(negative_run.stdout.strip(), "null")


if __name__ == "__main__":
    unittest.main()
