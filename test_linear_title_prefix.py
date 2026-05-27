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
                "id": "POI-4738",
                "title": "issue on 7911 and 7872",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
            },
        )

    def test_prefixes_linear_automation_trigger_payload_for_to_research(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "issue on 7911 and 7872",
                "id": "POI-4738",
                "url": "https://linear.app/atmen/issue/POI-4738/issue-on-7911-and-7872",
                "status": "To Research",
                "statusType": "unstarted",
                "priority": "Urgent",
                "project": "Lhyfe Issues",
                "labels": "No labels",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
            },
        )

    def test_ignores_non_matching_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4738",
                "title": "issue on 7911 and 7872",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4738",
                "title": "issue on 7911 and 7872",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4738",
                "title": "cursor researching: issue on 7911 and 7872",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_camel_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "issueId": "POI-4738",
                "title": "issue on 7911 and 7872",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "a2c0b6fd-76f1-4a65-95a8-6e6f765c902e",
                    "identifier": "POI-4738",
                    "title": "issue on 7911 and 7872",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
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
                    "identifier": "POI-4738",
                    "title": "issue on 7911 and 7872",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
            },
        )

    def test_ignores_old_status_value_when_new_status_differs(self):
        event = {
            "action": "update",
            "updatedFields": {
                "state": {
                    "from": {"name": "To Research"},
                    "to": {"name": "DEV"},
                }
            },
            "data": {
                "issue": {
                    "identifier": "POI-4738",
                    "title": "issue on 7911 and 7872",
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
                    "title": "issue on 7911 and 7872",
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
                        "title": "issue on 7911 and 7872",
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
                        "id": "POI-4738",
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
                "id": "POI-4738",
                "title": "issue on 7911 and 7872",
            },
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(linear_title_prefix.main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4738",
                "title": "Cursor researching: issue on 7911 and 7872",
            },
        )


if __name__ == "__main__":
    unittest.main()
