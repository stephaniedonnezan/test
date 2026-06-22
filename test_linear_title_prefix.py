import json
import subprocess
import sys
import unittest

from linear_title_prefix import ACTION, build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3676",
            "title": "Issues database",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": ACTION,
                "issueId": "POI-3676",
                "title": "Cursor researching: Issues database",
            },
        )

    def test_prefixes_cloud_trigger_context_status_change_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-3676",
                "title": "Issues database",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": ACTION,
                "issueId": "POI-3676",
                "title": "Cursor researching: Issues database",
            },
        )

    def test_supports_nested_linear_issue_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-3676",
                    "title": "Issues database",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": ACTION,
                "issueId": "POI-3676",
                "title": "Cursor researching: Issues database",
            },
        )

    def test_supports_status_from_changes_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {
                    "from": {"name": "Backlog"},
                    "to": {"name": "to_research"},
                }
            },
            "issueId": "POI-3676",
            "title": "Issues database",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": ACTION,
                "issueId": "POI-3676",
                "title": "Cursor researching: Issues database",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-3676",
                "title": "Issues database",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3676",
            "title": "Issues database",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-3676",
            "title": "Issues database",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-3676",
            "title": "cursor researching: Issues database",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3676",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3676",
            "title": "Issues database",
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
                "action": ACTION,
                "issueId": "POI-3676",
                "title": "Cursor researching: Issues database",
            },
        )


if __name__ == "__main__":
    unittest.main()
