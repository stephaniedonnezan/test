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
                "newStatus": "to research",
                "id": "POI-4531",
                "title": "Swagger Post uses a different timezone",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": "Cursor researching: Swagger Post uses a different timezone",
            },
        )

    def test_prefixes_automation_trigger_payload_for_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": (
                    "[Waiting for Shell's reply]Swagger Post using a different "
                    "timezone than Swagger Get and Swagger Delete"
                ),
                "id": "POI-4531",
                "url": (
                    "https://linear.app/atmen/issue/POI-4531/"
                    "waiting-for-shells-replyswagger-post-using-a-different-timezone-than"
                ),
                "status": "To Research",
                "statusType": "unstarted",
                "priority": "High",
                "assignee": "Unassigned",
                "project": "No project",
                "labels": "Bug",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": (
                    "Cursor researching: [Waiting for Shell's reply]Swagger Post "
                    "using a different timezone than Swagger Get and Swagger Delete"
                ),
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4531",
                "title": "Swagger Post uses a different timezone",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4531",
                "title": "Swagger Post uses a different timezone",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4531",
                "title": "cursor researching: Swagger Post uses a different timezone",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4531",
                "title": "Swagger Post uses a different timezone",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": "Cursor researching: Swagger Post uses a different timezone",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "identifier": "POI-4531",
                    "title": "Swagger Post uses a different timezone",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": "Cursor researching: Swagger Post uses a different timezone",
            },
        )

    def test_accepts_updated_fields_to_value_without_current_issue_state(self):
        event = {
            "action": "update",
            "updatedFields": {
                "workflowState": {
                    "from": {"name": "Todo"},
                    "to": {"name": "To Research"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-4531",
                    "title": "Swagger Post uses a different timezone",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": "Cursor researching: Swagger Post uses a different timezone",
            },
        )

    def test_ignores_old_status_value_when_new_status_differs(self):
        event = {
            "action": "update",
            "updatedFields": {
                "state": {
                    "from": {"name": "To Research"},
                    "to": {"name": "In Progress"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-4531",
                    "title": "Swagger Post uses a different timezone",
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_nested_issue_id_is_preferred_over_webhook_id(self):
        event = {
            "id": "webhook-event-id",
            "action": "update",
            "updatedFields": {"workflowState": {"from": "Todo", "to": "To Research"}},
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Swagger Post uses a different timezone",
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
                        "title": "Swagger Post uses a different timezone",
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
                        "id": "POI-4531",
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
                "id": "POI-4531",
                "title": "Swagger Post uses a different timezone",
            },
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4531",
                "title": "Cursor researching: Swagger Post uses a different timezone",
            },
        )


if __name__ == "__main__":
    unittest.main()
