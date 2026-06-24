import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_cloud_status_changed_to_research_returns_title_update(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4751",
                "title": "cursor researching: Knowledge support on a POS-related question",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "toResearch",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4751")
        self.assertEqual(
            result["title"],
            "Cursor researching: Knowledge support on a POS-related question",
        )

    def test_nested_linear_issue_update_with_updated_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4751",
                    "title": "Knowledge support on a POS-related question",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4751",
                "title": "Cursor researching: Knowledge support on a POS-related question",
            },
        )

    def test_nested_linear_changes_can_supply_new_status(self):
        event = {
            "type": "Issue Updated",
            "data": {
                "issue": {
                    "identifier": "POI-4751",
                    "title": "Knowledge support on a POS-related question",
                }
            },
            "changes": {
                "status": {
                    "oldValue": {"name": "Backlog"},
                    "newValue": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Knowledge support on a POS-related question",
        )

    def test_generic_issue_update_without_status_field_is_ignored(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4751",
                    "title": "Knowledge support on a POS-related question",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_id_or_title_is_ignored(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4751",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Knowledge support on a POS-related question",
                    }
                }
            )
        )

    def test_non_mapping_payload_is_ignored(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4751",
                "title": "Knowledge support on a POS-related question",
            }
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(json.loads(process.stdout)["action"], "update_issue_title")


if __name__ == "__main__":
    unittest.main()
