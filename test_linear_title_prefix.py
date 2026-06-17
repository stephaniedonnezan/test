import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_flat_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5044",
            "title": "Do we always know whether an offtaker has to report downstream emissions?",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5044",
                "title": (
                    "Cursor researching: Do we always know whether an offtaker has to "
                    "report downstream emissions?"
                ),
            },
        )

    def test_accepts_cursor_trigger_context_payload(self):
        event = {
            "automationId": "automation-123",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Clarify downstream emissions reporting",
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-123")
        self.assertEqual(update["title"], "Cursor researching: Clarify downstream emissions reporting")

    def test_accepts_status_name_variants(self):
        statuses = ("To Research", "to_research", "to-research", "toResearch")

        for status in statuses:
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "issueId": "POI-123",
                    "title": "Research me",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Research me",
                )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "cursor researching: Research me",
        }

        update = build_issue_title_update(event)

        self.assertEqual(update["title"], "cursor researching: Research me")

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Agent research to review",
            "id": "POI-123",
            "title": "Research me",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Research me",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_update_when_state_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["stateId"],
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-456",
                "title": "Cursor researching: Nested Linear issue",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "newStatus": "to research",
            "data": {
                "issue": {
                    "identifier": "POI-456",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_extracts_new_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": [{"field": "workflowState", "to": {"name": "To Research"}}],
            "issueId": "POI-789",
            "title": "Changed through workflow state",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed through workflow state",
        )

    def test_missing_issue_id_or_title_returns_none(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Run through CLI",
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
                "issueId": "POI-123",
                "title": "Cursor researching: Run through CLI",
            },
        )


if __name__ == "__main__":
    unittest.main()
