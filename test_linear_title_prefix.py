import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4247",
                "title": "Bulk Upload of container events",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4247",
                "title": "Cursor researching: Bulk Upload of container events",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-1",
            "title": "Investigate import flow",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate import flow",
            },
        )

    def test_supports_linear_issue_updated_payload_with_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-2",
                "title": "Research webhook",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Research webhook",
            },
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3",
            "title": "Do not update",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4",
            "title": "Already done",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_prefix_already_present(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_required_issue_fields_are_missing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-6",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-7",
            "title": "CLI payload",
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
                "issueId": "POI-7",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
