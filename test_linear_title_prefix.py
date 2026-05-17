import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4636",
            "title": "UBA POS in from external qualified input",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4636",
                "title": "Cursor researching: UBA POS in from external qualified input",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To_Research",
            "issueId": "POI-1",
            "title": "Research this",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Research this",
            },
        )

    def test_accepts_nested_linear_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-2",
                "title": "Nested issue",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Nested issue",
            },
        )

    def test_accepts_automation_trigger_context_payload(self):
        event = {
            "automationId": "automation",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Automation issue",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Automation issue",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-6",
            "title": "Do not prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "cursor researching: Already prefixed",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-8"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-9",
            "title": "CLI issue",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
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
