import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4903",
                "title": "Prevent event updates",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4903",
                "title": "Cursor researching: Prevent event updates",
            },
        )

    def test_returns_none_for_other_statuses(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4903",
                "title": "Prevent event updates",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_for_non_status_change_trigger(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4903",
                "title": "Prevent event updates",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_does_not_duplicate_existing_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4903",
                "title": "cursor researching: Prevent event updates",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_accepts_status_separator_and_camel_case_variants(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "identifier": "POI-4903",
                "title": "Prevent event updates",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4903",
                "title": "Cursor researching: Prevent event updates",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        payload = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4903",
                    "title": "Prevent event updates",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4903",
                "title": "Cursor researching: Prevent event updates",
            },
        )

    def test_requires_status_field_for_generic_update_payloads(self):
        payload = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4903",
                    "title": "Prevent event updates",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_cli_prints_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to-research",
                "id": "POI-4903",
                "title": "Prevent event updates",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4903",
                "title": "Cursor researching: Prevent event updates",
            },
        )


if __name__ == "__main__":
    unittest.main()
