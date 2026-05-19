import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_flat_automation_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_nested_linear_issue_update_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4483",
                "title": "Gather ETS daily prices",
                "state": {"name": "to-research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_accepts_camel_case_trigger_and_status(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
            "status": "to research",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4483",
            "title": "cursor researching: Gather ETS daily prices",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4483",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4483",
            "title": "Gather ETS daily prices",
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
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
