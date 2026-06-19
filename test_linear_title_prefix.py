import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    RESEARCHING_PREFIX,
    add_researching_prefix,
    build_issue_title_update,
    updated_title_for_status_change,
)


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-3023",
                "title": "Metric tonne to be used instead of ton",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-3023",
                "title": "Cursor researching: Metric tonne to be used instead of ton",
            },
        )

    def test_normalizes_status_and_trigger_names(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "identifier": "POI-3023",
                "title": "Normalize title",
            }
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching: Normalize title",
        )

    def test_ignores_other_statuses(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "issueId": "POI-3023",
                "title": "Metric tonne to be used instead of ton",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_ignores_non_status_change_events(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "issueId": "POI-3023",
                "title": "Metric tonne to be used instead of ton",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_generic_issue_update_requires_status_field(self):
        payload = {
            "triggerContext": {
                "trigger": "issue_updated",
                "updatedFields": ["description"],
                "newStatus": "to research",
                "issueId": "POI-3023",
                "title": "Metric tonne to be used instead of ton",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_generic_issue_update_accepts_status_field(self):
        payload = {
            "triggerContext": {
                "trigger": "issue_updated",
                "updatedFields": ["state"],
                "state": {"name": "to research"},
                "issueId": "POI-3023",
                "title": "Metric tonne to be used instead of ton",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-3023",
                "title": "Cursor researching: Metric tonne to be used instead of ton",
            },
        )

    def test_reads_nested_linear_issue_payload(self):
        payload = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": ["workflowState"],
            "data": {
                "issue": {
                    "id": "POI-3023",
                    "title": "Metric tonne wording",
                    "workflowState": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-3023",
                "title": "Cursor researching: Metric tonne wording",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-3023",
                "title": "Cursor researching: Metric tonne wording",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_adds_marker_for_empty_placeholder_title(self):
        self.assertEqual(add_researching_prefix("[]"), RESEARCHING_PREFIX)

    def test_cli_prints_update_action(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-3023",
                "title": "Metric tonne wording",
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
                "issueId": "POI-3023",
                "title": "Cursor researching: Metric tonne wording",
            },
        )


if __name__ == "__main__":
    unittest.main()
