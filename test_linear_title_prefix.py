import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_flat_cursor_automation_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4020",
            "title": "CertifHy feedback",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4020",
                "title": "Cursor researching: CertifHy feedback",
            },
        )

    def test_nested_cursor_automation_trigger_context(self):
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4020",
                "title": "[]CertifHy feedback",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4020",
                "title": "Cursor researching: []CertifHy feedback",
            },
        )

    def test_uses_status_fallback_from_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4020",
                "title": "CertifHy feedback",
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CertifHy feedback",
        )

    def test_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "id": "linear-uuid",
                    "identifier": "POI-4020",
                    "title": "CertifHy feedback",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4020",
                "title": "Cursor researching: CertifHy feedback",
            },
        )

    def test_accepts_separator_and_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "TO_RESEARCH",
            "issue_id": "POI-4020",
            "title": " CertifHy feedback ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: CertifHy feedback",
        )

    def test_returns_none_for_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4020",
            "title": "CertifHy feedback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4020",
            "title": "CertifHy feedback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_issue_update_without_status_field(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "id": "POI-4020",
                    "title": "CertifHy feedback",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_title_already_prefixed(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4020",
            "title": "cursor researching: CertifHy feedback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "CertifHy feedback",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_prints_update_action_for_matching_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4020",
            "title": "CertifHy feedback",
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
                "issueId": "POI-4020",
                "title": "Cursor researching: CertifHy feedback",
            },
        )


if __name__ == "__main__":
    unittest.main()
