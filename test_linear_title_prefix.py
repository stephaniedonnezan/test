import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-123",
                "title": "Investigate export headers",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate export headers",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4574",
            "title": "Delivery 7846 missing in Mass Balance Export",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-123",
            "title": "Investigate export headers",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-123",
            "title": "cursor researching: Investigate export headers",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_separator_and_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to-research",
            "id": "POI-124",
            "title": "  Check certificate accounting  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Check certificate accounting",
            },
        )

    def test_handles_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-456",
                "title": "Research mass-balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Research mass-balance export",
            },
        )

    def test_handles_workflow_state_update_payloads(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "identifier": "POI-789",
                "title": "Review hydrogen batch",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-789",
                "title": "Cursor researching: Review hydrogen batch",
            },
        )

    def test_ignores_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "id": "issue-uuid",
                "title": "Research mass-balance export",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "To Research"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-1"}
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))  # type: ignore[arg-type]
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))  # type: ignore[arg-type]

    def test_cli_prints_update_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-125",
            "title": "Trace missing delivery",
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
                "issueId": "POI-125",
                "title": "Cursor researching: Trace missing delivery",
            },
        )

    def test_cli_prints_nothing_for_non_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-125",
            "title": "Trace missing delivery",
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
