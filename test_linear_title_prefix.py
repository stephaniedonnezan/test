import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_for_cursor_status_changed_context(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3476",
                    "title": "Implement Unloading",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3476",
                "title": "Implement Unloading",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-3476",
                "title": "Implement Unloading",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3476",
                "title": "cursor researching: Implement Unloading",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_name_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-3476",
                "title": "Implement Unloading",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_accepts_nested_linear_issue_update_with_updated_fields(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3476",
                    "title": "Implement Unloading",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_requires_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["priority"],
            "data": {
                "issue": {
                    "identifier": "POI-3476",
                    "title": "Implement Unloading",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_new_status_from_changes_before_stale_issue_status(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-3476",
                    "title": "Implement Unloading",
                    "status": "Todo",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_accepts_list_changes_payload(self):
        event = {
            "action": "updated_issue",
            "changes": [{"field": "workflowState", "newValue": {"name": "To Research"}}],
            "issueId": "POI-3476",
            "title": "Implement Unloading",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "identifier": " POI-3476 ",
            "title": " Implement Unloading ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Implement Unloading",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "identifier": "POI-3476",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_safely_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))  # type: ignore[arg-type]

    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3476",
                "title": "Implement Unloading",
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
                "issueId": "POI-3476",
                "title": "Cursor researching: Implement Unloading",
            },
        )


if __name__ == "__main__":
    unittest.main()
