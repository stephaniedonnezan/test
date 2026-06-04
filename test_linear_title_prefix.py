import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_flat_status_changed_to_research_prefixes_title(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4255",
                "title": (
                    "Add external connectors into the container logic. "
                    "Case: Producer --> Container-Trader"
                ),
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4255",
                "title": (
                    "Cursor researching: Add external connectors into the "
                    "container logic. Case: Producer --> Container-Trader"
                ),
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "issueId": "POI-4255",
            "title": "Add external connectors into the container logic",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4255",
                "title": (
                    "Cursor researching: Add external connectors into the "
                    "container logic"
                ),
            },
        )

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["description", "workflowState"],
            "data": {
                "issue": {
                    "identifier": "POI-4255",
                    "title": "Add external connectors into container logic",
                    "workflowState": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4255",
                "title": (
                    "Cursor researching: Add external connectors into "
                    "container logic"
                ),
            },
        )

    def test_ignores_done_status_from_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4255",
                "title": "Add external connectors into container logic",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4255",
            "title": "Add external connectors into container logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4255",
            "title": "Add external connectors into container logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_update_without_status_field_change(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "status": "to research",
            "id": "POI-4255",
            "title": "Add external connectors into container logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4255",
            "title": "cursor researching: Add external connectors into logic",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4255",
            "title": " ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4255",
                "title": "Add external connectors into container logic",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4255",
                "title": (
                    "Cursor researching: Add external connectors into "
                    "container logic"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
