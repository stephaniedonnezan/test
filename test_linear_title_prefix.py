import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_payload_prefixes_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )

    def test_status_field_is_used_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "status": "to research",
                "issueId": "abc123",
                "title": "Investigate pricing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate pricing",
        )

    def test_status_normalization_accepts_separators_and_case(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "new_status": "TO_RESEARCH",
                "identifier": "POI-1",
                "title": "Review source data",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_non_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4811",
                "title": "Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4811",
                "title": "cursor researching: Create production site form",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_linear_update_payload_with_state_change(self):
        event = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state"},
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Map feedstock constraints",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Map feedstock constraints",
            },
        )

    def test_nested_linear_update_payload_with_workflow_state_change(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["workflowState"],
            "data": {
                "id": "issue-uuid",
                "title": "Trace emissions source",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trace emissions source",
        )

    def test_ignores_generic_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-uuid",
                "title": "Map feedstock constraints",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4811",
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
                        "title": "Missing issue id",
                    }
                }
            )
        )

    def test_cli_outputs_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4811",
                "title": "Create production site form",
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
                "issueId": "POI-4811",
                "title": "Cursor researching: Create production site form",
            },
        )


if __name__ == "__main__":
    unittest.main()
