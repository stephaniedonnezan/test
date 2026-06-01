import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "cursor researching: Custom LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Custom LHV",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_requires_status_field_for_generic_issue_update(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "id": "issue-uuid",
                    "title": "Custom LHV",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_prefers_nested_issue_id_over_outer_automation_id(self):
        event = {
            "automationId": "automation-uuid",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issue": {
                    "id": "POI-4733",
                    "title": "Custom LHV",
                },
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4733")

    def test_handles_workflow_state_objects(self):
        event = {
            "webhookType": "workflowStateChanged",
            "data": {
                "id": "POI-4733",
                "title": "Custom LHV",
                "workflowState": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )

    def test_requires_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4733",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_json_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4733",
                "title": "Custom LHV",
            }
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            exit_code = linear_title_prefix.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4733",
                "title": "Cursor researching: Custom LHV",
            },
        )


if __name__ == "__main__":
    unittest.main()
