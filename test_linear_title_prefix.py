import json
import subprocess
import sys
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_payload(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs in container view",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: Issues panel must be visible across all tabs in container view",
            },
        )

    def test_accepts_status_separator_and_case_variations(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": "POI-1",
                "title": "Investigate title handling",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate title handling",
            },
        )

    def test_skips_non_research_status(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs in container view",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4934",
                "title": "Issues panel must be visible across all tabs in container view",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4934",
                "title": "cursor researching: Issues panel",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_uses_nested_linear_issue_update_payload(self) -> None:
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "updatedFields": ["state"],
                "issue": {
                    "identifier": "POI-22",
                    "title": "Check nested Linear payloads",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-22",
                "title": "Cursor researching: Check nested Linear payloads",
            },
        )

    def test_uses_changes_new_status_before_current_status(self) -> None:
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-23",
                    "title": "Read status from change details",
                    "state": {"name": "Backlog"},
                },
                "changes": {
                    "state": {
                        "old": {"name": "Backlog"},
                        "new": {"name": "To Research"},
                    }
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-23",
                "title": "Cursor researching: Read status from change details",
            },
        )

    def test_requires_title_and_issue_id(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Missing id",
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
                        "id": "POI-4934",
                    }
                }
            )
        )

    def test_cli_reads_json_from_stdin(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4934",
                "title": "CLI smoke test",
            }
        }

        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("linear_title_prefix.py"))],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4934",
                "title": "Cursor researching: CLI smoke test",
            },
        )
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
