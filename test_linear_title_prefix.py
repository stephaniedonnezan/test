import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_status_changed_to_research_adds_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4837",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )

    def test_status_changed_uses_status_when_new_status_absent(self):
        payload = {
            "trigger": "statusChanged",
            "status": "To Research",
            "issueId": "POI-1",
            "title": "Investigate allocation",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate allocation",
            },
        )

    def test_status_matching_is_case_and_separator_insensitive(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "identifier": "POI-2",
                "title": "Add report",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Add report",
        )

    def test_non_research_status_is_ignored(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_non_status_change_trigger_is_ignored(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "status": "to research",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_existing_prefix_is_not_duplicated(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4837",
                "title": "cursor researching: Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_missing_issue_id_is_ignored(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Gather ETS daily prices",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_missing_title_is_ignored(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4837",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_nested_linear_update_with_state_change_is_supported(self):
        payload = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-3",
                    "title": "Research nested payload",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-3",
                "title": "Cursor researching: Research nested payload",
            },
        )

    def test_updated_from_state_id_counts_as_status_change(self):
        payload = {
            "type": "Issue Updated",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "issue": {
                    "identifier": "POI-4",
                    "title": "Research updatedFrom",
                    "workflowState": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Research updatedFrom",
        )

    def test_update_without_status_field_change_is_ignored(self):
        payload = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-5",
                    "title": "Title-only update",
                    "state": {"name": "to research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4837",
                "title": "Gather ETS daily prices",
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
                "issueId": "POI-4837",
                "title": "Cursor researching: Gather ETS daily prices",
            },
        )


if __name__ == "__main__":
    unittest.main()
