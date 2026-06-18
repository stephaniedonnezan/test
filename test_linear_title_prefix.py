import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_flat_status_changed_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5040",
                "title": "Create the SiteIsNotProcessingUnitError",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-5040",
            "title": "Investigate production outputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Investigate production outputs",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-5040",
            "title": "Create the SiteIsNotProcessingUnitError",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "Create the SiteIsNotProcessingUnitError",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "cursor researching: Create the SiteIsNotProcessingUnitError",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5040",
                "title": "Create the SiteIsNotProcessingUnitError",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-uuid",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "action": "issue_updated",
            "changes": {"workflowState": {"from": "Backlog", "to": {"name": "To Research"}}},
            "issue": {
                "identifier": "POI-5040",
                "title": "Create the SiteIsNotProcessingUnitError",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )

    def test_returns_none_for_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5040",
            "title": "Create the SiteIsNotProcessingUnitError",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5040",
                "title": "Cursor researching: Create the SiteIsNotProcessingUnitError",
            },
        )


if __name__ == "__main__":
    unittest.main()
