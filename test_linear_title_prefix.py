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
                "newStatus": "To Research",
                "id": "POI-5017",
                "title": "There seems to be a minimum value when allocating to a prod site",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5017",
                "title": (
                    "Cursor researching: There seems to be a minimum value when "
                    "allocating to a prod site"
                ),
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "issueId": "POI-5017",
                "title": "Allocation field silently corrects values",
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(
            update["title"],
            "Cursor researching: Allocation field silently corrects values",
        )

    def test_ignores_non_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5017",
                "title": "Allocation field silently corrects values",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5017",
                "title": "Allocation field silently corrects values",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5017",
                "title": "cursor researching: Allocation field silently corrects values",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-5017",
                    "title": "Allocation field silently corrects values",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFields": ["state"],
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5017",
                "title": "Cursor researching: Allocation field silently corrects values",
            },
        )

    def test_reads_new_status_from_changes(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-5017",
                    "title": "Allocation field silently corrects values",
                }
            },
            "changes": [
                {
                    "field": "workflowState",
                    "oldValue": {"name": "Todo"},
                    "newValue": {"name": "To Research"},
                }
            ],
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-5017")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-5017",
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
                        "title": "Allocation field silently corrects values",
                    }
                }
            )
        )


class CliTest(unittest.TestCase):
    def test_cli_outputs_update_json(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5017",
                "title": "Allocation field silently corrects values",
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
                "issueId": "POI-5017",
                "title": "Cursor researching: Allocation field silently corrects values",
            },
        )

    def test_cli_is_quiet_when_no_update_is_needed(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5017",
                "title": "Allocation field silently corrects values",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
