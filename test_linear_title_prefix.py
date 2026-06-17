import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class UpdateIssueTitleForStatusTest(unittest.TestCase):
    def test_adds_cursor_researching_for_to_research_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Auditor can access Producer page through direct URL",
                new_status="to research",
            ),
            "Cursor researching: Auditor can access Producer page through direct URL",
        )

    def test_status_match_accepts_case_whitespace_and_separators(self) -> None:
        for status in ("To Research", " to_research ", "to-research", "toResearch"):
            with self.subTest(status=status):
                self.assertEqual(
                    update_issue_title_for_status("Issue title", status),
                    "Cursor researching: Issue title",
                )

    def test_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            update_issue_title_for_status("Issue title", "Todo"),
            "Issue title",
        )

    def test_does_not_duplicate_existing_marker(self) -> None:
        for title in (
            "Cursor researching: Issue title",
            "cursor researching - Issue title",
            "Cursor researching Issue title",
        ):
            with self.subTest(title=title):
                self.assertEqual(
                    update_issue_title_for_status(title, "to research"),
                    title,
                )


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_change_payload(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4977",
                "title": "Auditor can access Producer page through direct URL",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": (
                    "Cursor researching: Auditor can access Producer page through "
                    "direct URL"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4977",
                "title": "Auditor can access Producer page through direct URL",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4977",
                "title": "Auditor can access Producer page through direct URL",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4977",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4977",
                    "title": "Auditor can access Producer page through direct URL",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": (
                    "Cursor researching: Auditor can access Producer page through "
                    "direct URL"
                ),
            },
        )

    def test_ignores_generic_update_without_status_field_change(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4977",
                    "title": "Auditor can access Producer page through direct URL",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_change_object_target_status(self) -> None:
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": "toResearch"}},
            "data": {
                "issue": {
                    "identifier": "POI-4977",
                    "title": "Auditor can access Producer page through direct URL",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": (
                    "Cursor researching: Auditor can access Producer page through "
                    "direct URL"
                ),
            },
        )

    def test_requires_issue_id_and_title(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4977",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


class DeriveUpdatedTitleTest(unittest.TestCase):
    def test_returns_updated_title_without_requiring_issue_id(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(event),
            "Cursor researching: Issue title",
        )


class CliTest(unittest.TestCase):
    def test_cli_reads_input_file_and_prints_update_action(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4977",
                "title": "Issue title",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(event), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4977",
                "title": "Cursor researching: Issue title",
            },
        )


if __name__ == "__main__":
    unittest.main()
