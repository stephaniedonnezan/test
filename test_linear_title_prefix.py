import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title
from linear_title_prefix import prefix_research_title
from linear_title_prefix import update_issue_title_for_status


class PrefixResearchTitleTests(unittest.TestCase):
    def test_adds_prefix_to_title(self) -> None:
        self.assertEqual(
            prefix_research_title("Issues should always try to link"),
            "Cursor researching - Issues should always try to link",
        )

    def test_trims_title_before_prefixing(self) -> None:
        self.assertEqual(
            prefix_research_title("  Issues should always try to link  "),
            "Cursor researching - Issues should always try to link",
        )

    def test_empty_title_returns_prefix_only(self) -> None:
        self.assertEqual(prefix_research_title("  "), "Cursor researching")

    def test_does_not_duplicate_prefix_with_hyphen(self) -> None:
        self.assertEqual(
            prefix_research_title("Cursor researching - Existing title"),
            "Cursor researching - Existing title",
        )

    def test_does_not_duplicate_prefix_with_colon(self) -> None:
        self.assertEqual(
            prefix_research_title("cursor researching: Existing title"),
            "cursor researching: Existing title",
        )

    def test_does_not_duplicate_bare_prefix(self) -> None:
        self.assertEqual(
            prefix_research_title("Cursor researching Existing title"),
            "Cursor researching Existing title",
        )


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_prefix_for_to_research(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Issues should always try to link",
                new_status="to research",
            ),
            "Cursor researching - Issues should always try to link",
        )

    def test_status_match_is_case_and_separator_insensitive(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Issue title",
                new_status="  To_Research ",
            ),
            "Cursor researching - Issue title",
        )

    def test_no_change_for_other_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Issue title",
                new_status="Agent research to review",
            ),
            "Issue title",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_for_automation_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_returns_updated_title_for_raw_status_changed_payload(self) -> None:
        payload = {
            "trigger": "status changed",
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_status_fallback_field(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_supports_nested_linear_issue_payload(self) -> None:
        payload = {
            "type": "Issue",
            "action": "update",
            "updatedFrom": {"workflowStateId": "old-state-id"},
            "data": {
                "id": "issue-id",
                "title": "Issue title",
                "state": {"name": "to research"},
            },
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Issue title",
        )

    def test_returns_none_for_non_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_added",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_status_does_not_match(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_prefix_already_exists(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payload(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "bad"}))
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_builds_action_with_issue_id_when_available(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5020",
                "title": "Issues should always try to link",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-5020",
                "title": "Cursor researching - Issues should always try to link",
            },
        )

    def test_builds_action_without_issue_id_when_unavailable(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "title": "Cursor researching - Issue title",
            },
        )


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "linear_title_prefix.py", "--input", str(payload_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching - Issue title"},
        )

    def test_cli_can_return_action_payload(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "issue-id",
                "title": "Issue title",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "linear_title_prefix.py",
                    "--input",
                    str(payload_path),
                    "--action",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching - Issue title",
            },
        )


if __name__ == "__main__":
    unittest.main()
