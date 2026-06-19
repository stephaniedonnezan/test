import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_status_change_to_research_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4382",
                "title": "Allow overrides in spreadheets on test comparisons",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Allow overrides in spreadheets on test comparisons",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4382",
                "title": "Allow overrides in spreadheets on test comparisons",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4382",
                "title": "Allow overrides in spreadheets on test comparisons",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4382",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "cursor researching: Existing title",
            },
        )

    def test_accepts_nested_linear_issue_updated_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4382",
                    "title": "Allow overrides in spreadheets on test comparisons",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Allow overrides in spreadheets on test comparisons",
            },
        )

    def test_accepts_status_from_changes(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"to": {"name": "to_research"}}},
            "issue": {
                "id": "POI-4382",
                "title": "Allow overrides in spreadheets on test comparisons",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4382",
                "title": "Cursor researching: Allow overrides in spreadheets on test comparisons",
            },
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4382",
                "title": "Allow overrides in spreadheets on test comparisons",
            }
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
                "issueId": "POI-4382",
                "title": "Cursor researching: Allow overrides in spreadheets on test comparisons",
            },
        )


if __name__ == "__main__":
    unittest.main()
