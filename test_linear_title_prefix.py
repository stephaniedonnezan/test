import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4774",
            "title": "Misrepresentation of co2 stock/delivery in mass balance export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: Misrepresentation of co2 stock/delivery "
                    "in mass balance export"
                ),
            },
        )

    def test_accepts_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4774",
                "title": "Misrepresentation of co2 stock/delivery in mass balance export",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: Misrepresentation of co2 stock/delivery "
                    "in mass balance export"
                ),
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4774",
                "title": "Misrepresentation of co2 stock/delivery in mass balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: Misrepresentation of co2 stock/delivery "
                    "in mass balance export"
                ),
            },
        )

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4774",
            "title": "Misrepresentation of co2 stock/delivery in mass balance export",
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_prefers_explicit_new_status_over_nested_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4774",
                "title": "Misrepresentation of co2 stock/delivery in mass balance export",
            },
            "data": {
                "state": {"name": "QA"},
            },
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": "Misrepresentation of co2 stock/delivery in mass balance export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-4774",
            "title": "Misrepresentation of co2 stock/delivery in mass balance export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4774",
                "title": "Misrepresentation of co2 stock/delivery in mass balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": (
                "cursor researching: Misrepresentation of co2 stock/delivery "
                "in mass balance export"
            ),
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_invalid_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update({}))

    def test_cli_outputs_update_action_for_matching_event(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4774",
            "title": "Misrepresentation of co2 stock/delivery in mass balance export",
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
                "issueId": "POI-4774",
                "title": (
                    "Cursor researching: Misrepresentation of co2 stock/delivery "
                    "in mass balance export"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
