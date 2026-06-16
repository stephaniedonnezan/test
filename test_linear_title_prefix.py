import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_change_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4965",
            "title": (
                "performance: fetch the meter readings only once when calculating "
                "the grid mix"
            ),
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": (
                    "Cursor researching: performance: fetch the meter readings only "
                    "once when calculating the grid mix"
                ),
            },
        )

    def test_prefixes_trigger_context_payload(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4965",
                "title": "Calculate grid mix from existing meter readings",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": (
                    "Cursor researching: Calculate grid mix from existing meter "
                    "readings"
                ),
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4965",
                "title": "Reuse power-consumption meter readings",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Reuse power-consumption meter readings",
            },
        )

    def test_accepts_changed_status_new_value(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["status"],
            "issue": {
                "issueId": "POI-4965",
                "title": "Investigate duplicate meter reading fetches",
            },
            "changes": {"status": {"oldValue": "Backlog", "newValue": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4965",
                "title": "Cursor researching: Investigate duplicate meter reading fetches",
            },
        )

    def test_normalizes_status_separators_and_casing(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "identifier": "POI-4965",
            "title": "Normalize status names",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize status names",
        )

    def test_prefers_issue_identifier_over_webhook_event_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4965",
                "title": "Use the issue identifier",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4965")

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "cursor researching: Existing research issue",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "cursor researching: Existing research issue",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4965",
            "title": "Do not update in-progress issues",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_updates(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4965",
                "title": "Title-only edit",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_state_name_is_not_used_as_missing_title(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4965",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4965",
            "title": "CLI payload",
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
                "issueId": "POI-4965",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
