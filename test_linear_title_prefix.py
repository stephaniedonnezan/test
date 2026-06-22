import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_cursor_trigger_context_for_to_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4809",
                "title": "Cursor researching: Reduce number of entityManager.save to one.",
            },
        )

    def test_automation_trigger_context_wrapper(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4809",
                "title": "Reduce number of entityManager.save to one.",
            },
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4809")
        self.assertEqual(
            result["title"],
            "Cursor researching: Reduce number of entityManager.save to one.",
        )

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4809",
                    "title": "Load May 2026 for Lhyfe",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Load May 2026 for Lhyfe",
                )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA Backend",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_update_without_status_field_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_generic_issue_update_with_status_field_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["status"],
            "status": "to research",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Reduce number of entityManager.save to one.",
        )

    def test_nested_linear_issue_update_uses_state_name(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-4809",
                "title": "Reduce number of entityManager.save to one.",
                "state": {"name": "To Research"},
                "updatedFields": ["state"],
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Reduce number of entityManager.save to one.",
            },
        )

    def test_changes_object_can_mark_status_update(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Backlog", "to": "To Research"}},
            "workflowState": {"name": "To Research"},
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Reduce number of entityManager.save to one.",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4809",
            "title": "cursor researching: Reduce number of entityManager.save to one.",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        base_event = {"trigger": "status_changed", "newStatus": "to research"}

        self.assertIsNone(build_issue_title_update({**base_event, "title": "Missing id"}))
        self.assertIsNone(build_issue_title_update({**base_event, "id": "POI-4809"}))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4809",
            "title": "Reduce number of entityManager.save to one.",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4809",
                "title": "Cursor researching: Reduce number of entityManager.save to one.",
            },
        )


if __name__ == "__main__":
    unittest.main()
