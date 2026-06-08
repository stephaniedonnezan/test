import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_updates_title_for_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4837",
                "title": "(WIP) QA report POI-4483 Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: (WIP) QA report POI-4483 Gather ETS daily prices",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4837",
                "title": "cursor researching: Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_status_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4837",
                    "title": "Gather ETS daily prices",
                    "state": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_ignores_linear_issue_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4837",
                    "title": "Gather ETS daily prices",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_status_from_change_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
            "issue": {
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4837",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_for_status_change_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4837",
                "title": "(WIP) QA report POI-4483 Gather ETS daily prices",
            }
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
                "issueId": "POI-4837",
                "title": "Cursor researching: (WIP) QA report POI-4483 Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
