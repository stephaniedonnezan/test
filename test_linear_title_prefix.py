import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload_for_to_research(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4311",
                "title": "Downstream emissions dialog refinement",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4311",
                "title": "Cursor researching: Downstream emissions dialog refinement",
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4311",
                "title": "Downstream emissions dialog refinement",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4311",
                "title": "Downstream emissions dialog refinement",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4311",
                "title": "cursor researching: Downstream emissions dialog refinement",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4311",
                "title": "Downstream emissions dialog refinement",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4311",
                "title": "Cursor researching: Downstream emissions dialog refinement",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "identifier": "POI-4311",
                    "title": "Downstream emissions dialog refinement",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4311",
                "title": "Cursor researching: Downstream emissions dialog refinement",
            },
        )

    def test_nested_issue_id_is_preferred_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Downstream emissions dialog refinement",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "linear-issue-id")

    def test_requires_issue_title_and_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Downstream emissions dialog refinement",
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
                        "id": "POI-4311",
                    }
                }
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not a payload"))

    def test_cli_prints_update_action_json(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4311",
                "title": "Downstream emissions dialog refinement",
            },
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4311",
                "title": "Cursor researching: Downstream emissions dialog refinement",
            },
        )


if __name__ == "__main__":
    unittest.main()
