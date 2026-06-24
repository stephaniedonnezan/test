import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3435",
                "title": "Close turn",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3435",
                "title": "Cursor researching: Close turn",
            },
        )

    def test_accepts_case_and_separator_variants_for_target_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-3435",
            "title": "Close turn",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3435",
            "title": "Close turn",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3435",
            "title": "cursor researching: Close turn",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-55",
                "title": "Map supplier inputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-55",
                "title": "Cursor researching: Map supplier inputs",
            },
        )

    def test_ignores_generic_issue_update_without_status_change_evidence(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-55",
                "title": "Map supplier inputs",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research"})
        )

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-99",
            "title": "Review biomass data",
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
                "issueId": "POI-99",
                "title": "Cursor researching: Review biomass data",
            },
        )


if __name__ == "__main__":
    unittest.main()
