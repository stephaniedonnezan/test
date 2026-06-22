import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4874",
                "title": "Containers tab action bar has empty lane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )

    def test_accepts_direct_trigger_context_payload(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "To Research",
            "issueId": "POI-4874",
            "title": "Containers tab action bar has empty lane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )

    def test_accepts_nested_linear_update_when_status_field_changed(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4874",
                    "title": "Containers tab action bar has empty lane",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )

    def test_reads_changed_status_value_from_changes(self):
        event = {
            "type": "Issue Updated",
            "changes": {"status": {"from": "Backlog", "to": "toResearch"}},
            "data": {
                "id": "issue-id",
                "identifier": "POI-4874",
                "title": "Containers tab action bar has empty lane",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )

    def test_ignores_non_status_change_update(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-4874",
                "title": "Containers tab action bar has empty lane",
                "state": {"name": "to research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4874",
                "title": "Containers tab action bar has empty lane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4874",
            "title": "cursor researching: Containers tab action bar has empty lane",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payloads_without_issue_identity_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Containers tab action bar has empty lane",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4874",
                }
            )
        )

    def test_cli_outputs_action_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4874",
                "title": "Containers tab action bar has empty lane",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4874",
                "title": "Cursor researching: Containers tab action bar has empty lane",
            },
        )


if __name__ == "__main__":
    unittest.main()
