import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_status_changed_to_research_trigger_context(self):
        event = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4483",
                "title": "[]Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: []Gather ETS daily prices",
            },
        )

    def test_accepts_case_and_separator_variations(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather ETS daily prices",
        )

    def test_falls_back_to_current_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Gather ETS daily prices",
        )

    def test_supports_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_issue_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "cursor researching: Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4483",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Gather ETS daily prices",
                    }
                }
            )
        )

    def test_cli_outputs_update_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4483",
                "title": "Gather ETS daily prices",
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
                "issueId": "POI-4483",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
