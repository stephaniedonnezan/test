import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_issue_title import build_issue_title_update
from linear_issue_title import derive_updated_title
from linear_issue_title import prefix_research_title
from linear_issue_title import update_issue_title_for_status


class PrefixResearchTitleTests(unittest.TestCase):
    def test_prefixes_title(self) -> None:
        self.assertEqual(
            prefix_research_title("Create production site form"),
            "Cursor researching - Create production site form",
        )

    def test_strips_outer_title_whitespace(self) -> None:
        self.assertEqual(
            prefix_research_title("  Create production site form  "),
            "Cursor researching - Create production site form",
        )

    def test_returns_prefix_for_empty_title(self) -> None:
        self.assertEqual(prefix_research_title("   "), "Cursor researching")

    def test_does_not_duplicate_existing_prefix(self) -> None:
        titles = (
            "Cursor researching Create production site form",
            "Cursor researching - Create production site form",
            "Cursor researching: Create production site form",
            "cursor researching - Create production site form",
        )

        for title in titles:
            with self.subTest(title=title):
                self.assertEqual(prefix_research_title(title), title)


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_prefix_for_to_research_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Create production site form",
                new_status="to research",
            ),
            "Cursor researching - Create production site form",
        )

    def test_status_match_is_case_whitespace_and_separator_insensitive(self) -> None:
        statuses = ("To Research", "  to   research  ", "to-research", "to_research")

        for status in statuses:
            with self.subTest(status=status):
                self.assertEqual(
                    update_issue_title_for_status("Issue title", status),
                    "Cursor researching - Issue title",
                )

    def test_leaves_title_unchanged_for_other_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status("Issue title", "Done"),
            "Issue title",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_matches_current_linear_automation_payload_shape(self) -> None:
        payload = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Create production site form",
                "id": "POI-4811",
            },
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Create production site form",
        )

    def test_builds_issue_update_for_current_payload_shape(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Create production site form",
                "id": "POI-4811",
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "issueId": "POI-4811",
                "title": "Cursor researching - Create production site form",
            },
        )

    def test_supports_nested_issue_payload_shape(self) -> None:
        payload = {
            "trigger": "workflow_state_updated",
            "data": {
                "issue": {
                    "id": "issue-id",
                    "title": "Issue title",
                    "state": {"name": "to research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "issueId": "issue-id",
                "title": "Cursor researching - Issue title",
            },
        )

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
                "id": "POI-4811",
            },
        }

        self.assertIsNone(derive_updated_title(payload))
        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_for_non_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "Issue title",
                "id": "POI-4811",
            },
        }

        self.assertIsNone(derive_updated_title(payload))
        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_when_title_is_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Issue title",
                "id": "POI-4811",
            },
        }

        self.assertIsNone(derive_updated_title(payload))
        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_for_malformed_payloads(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "bad"}))
        self.assertIsNone(build_issue_title_update({"triggerContext": {}}))


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_update_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Create production site form",
                "id": "POI-4811",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_issue_title.py", "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "update": {
                    "issueId": "POI-4811",
                    "title": "Cursor researching - Create production site form",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
