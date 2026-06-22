import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5035",
                "title": "LHV versioning & traceability",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )

    def test_prefixes_flat_automation_trigger_context_from_cloud_payload(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-123",
                    "title": "Validate biomethane dashboard",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Validate biomethane dashboard",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-42",
                    "title": "Investigate data import",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-42",
                "title": "Cursor researching: Investigate data import",
            },
        )

    def test_accepts_generic_issue_update_when_updated_fields_include_status(self):
        event = {
            "action": "update",
            "updatedFields": ["priority", "state"],
            "newStatus": "To Research",
            "issueId": "POI-77",
            "title": "Research methane conversion",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-77",
                "title": "Cursor researching: Research methane conversion",
            },
        )

    def test_reads_changed_status_before_stale_nested_issue_state(self):
        event = {
            "action": "Issue Updated",
            "changes": {"state": {"from": "Backlog", "to": "To Research"}},
            "data": {
                "issue": {
                    "identifier": "POI-88",
                    "title": "Trace historical factor",
                    "state": {"name": "Backlog"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-88",
                "title": "Cursor researching: Trace historical factor",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        base_event = {
            "trigger": "statusChanged",
            "issueId": "POI-9",
            "title": "Title",
        }

        for status in ("to_research", "to-research", "toResearch", " TO  RESEARCH "):
            with self.subTest(status=status):
                event = {**base_event, "newStatus": status}
                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Title",
                )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "issueId": "POI-5035",
            "title": "LHV versioning & traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "issueId": "POI-5035",
            "title": "LHV versioning & traceability",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_generic_issue_update_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "status": "To Research",
            "issueId": "POI-19",
            "title": "Already researched title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-11",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        base_event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-12",
            "title": "Missing field check",
        }

        self.assertIsNone(build_issue_title_update({**base_event, "issueId": "  "}))
        self.assertIsNone(build_issue_title_update({**base_event, "title": "  "}))

    def test_cli_prints_title_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-5035",
            "title": "LHV versioning & traceability",
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
                "issueId": "POI-5035",
                "title": "Cursor researching: LHV versioning & traceability",
            },
        )


if __name__ == "__main__":
    unittest.main()
