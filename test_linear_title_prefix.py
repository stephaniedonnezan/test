import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3765",
                "title": "Refine Site Details>KPIs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3765",
                "title": "Cursor researching: Refine Site Details>KPIs",
            },
        )

    def test_ignores_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-3765",
                "title": "Refine Site Details>KPIs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3765",
                "title": "Refine Site Details>KPIs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-3765",
            "title": "cursor researching: Refine Site Details>KPIs",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_linear_update_payload_with_changed_state(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "identifier": "POI-3765",
                "title": "Refine Site Details>KPIs",
                "state": {"name": "toResearch"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3765",
                "title": "Cursor researching: Refine Site Details>KPIs",
            },
        )

    def test_cli_prints_update_action(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to-research",
            "issueId": "POI-3765",
            "title": "Refine Site Details>KPIs",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3765",
                "title": "Cursor researching: Refine Site Details>KPIs",
            },
        )


if __name__ == "__main__":
    unittest.main()
