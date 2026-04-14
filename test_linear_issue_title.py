import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from linear_issue_title import build_updated_title


class BuildUpdatedTitleTests(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[][Dev] - Refine Site Details>KPIs",
            }
        }
        self.assertEqual(
            build_updated_title(payload),
            "Cursor researching - [][Dev] - Refine Site Details>KPIs",
        )

    def test_no_change_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA UX/UI",
                "title": "Task title",
            }
        }
        self.assertEqual(build_updated_title(payload), "Task title")

    def test_no_change_for_other_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Task title",
            }
        }
        self.assertEqual(build_updated_title(payload), "Task title")

    def test_does_not_duplicate_existing_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Task title",
            }
        }
        self.assertEqual(build_updated_title(payload), "Cursor researching - Task title")

    def test_accepts_trigger_format_variants(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "Status-Changed",
                "newStatus": "to research",
                "title": "Task title",
            }
        }
        self.assertEqual(build_updated_title(payload), "Cursor researching - Task title")

    def test_falls_back_to_root_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Task title",
        }
        self.assertEqual(build_updated_title(payload), "Cursor researching - Task title")

    def test_returns_empty_when_title_missing(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
            }
        }
        self.assertEqual(build_updated_title(payload), "")


class CliTests(unittest.TestCase):
    SCRIPT = Path(__file__).resolve().parent / "linear_issue_title.py"

    def test_cli_reads_input_file_and_prints_json(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Task title",
            }
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as f:
            json.dump(payload, f)
            f.flush()
            completed = subprocess.run(
                [sys.executable, str(self.SCRIPT), "--input", f.name],
                check=True,
                capture_output=True,
                text=True,
            )
        parsed = json.loads(completed.stdout)
        self.assertEqual(parsed["updatedTitle"], "Cursor researching - Task title")

    def test_cli_reads_stdin(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Task title",
            }
        }
        completed = subprocess.run(
            [sys.executable, str(self.SCRIPT)],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )
        parsed = json.loads(completed.stdout)
        self.assertEqual(parsed["updatedTitle"], "Cursor researching - Task title")


if __name__ == "__main__":
    unittest.main()
