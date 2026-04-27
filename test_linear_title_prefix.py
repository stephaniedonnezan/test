import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_title_prefix import add_researching_prefix
from linear_title_prefix import build_issue_title_update
from linear_title_prefix import derive_updated_title


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4559",
                "title": "Transport Events have way to low emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4559",
                "title": "Cursor researching: Transport Events have way to low emissions",
            },
        )

    def test_uses_status_when_new_status_is_absent(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-1",
                "title": "Investigate transport emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate transport emissions",
            },
        )

    def test_accepts_flat_webhook_payload(self) -> None:
        event = {
            "trigger": "STATUS CHANGED",
            "newStatus": "TO_RESEARCH",
            "id": "POI-2",
            "title": "Review certificate ingestion",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Review certificate ingestion",
            },
        )

    def test_ignores_other_triggers(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Research mass balance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4",
                "title": "Research mass balance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "Cursor researching: Research mass balance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_check_accepts_hyphen_separator(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "cursor researching - Research mass balance",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self) -> None:
        missing_issue_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research mass balance",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_issue_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_returns_none_for_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class TitlePrefixTest(unittest.TestCase):
    def test_add_researching_prefix_trims_title(self) -> None:
        self.assertEqual(
            add_researching_prefix("  Investigate feedstock data  "),
            "Cursor researching: Investigate feedstock data",
        )

    def test_derive_updated_title_returns_only_title(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "Investigate feedstock data",
            }
        }

        self.assertEqual(
            derive_updated_title(event),
            "Cursor researching: Investigate feedstock data",
        )


class CliTest(unittest.TestCase):
    def test_cli_reads_input_file_and_returns_json_output(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
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
            {"updatedTitle": "Cursor researching: Issue title"},
        )


if __name__ == "__main__":
    unittest.main()
