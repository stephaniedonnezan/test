import json
import subprocess
import sys
from pathlib import Path

from linear_issue_title import update_title


def test_prefix_added_for_status_changed_to_research() -> None:
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Improve debug signal",
        }
    }

    assert update_title(payload) == {
        "updatedTitle": "Cursor researching - Improve debug signal"
    }


def test_no_change_for_other_status() -> None:
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "title": "Improve debug signal",
        }
    }

    assert update_title(payload) == {"updatedTitle": "Improve debug signal"}


def test_no_change_for_other_trigger() -> None:
    payload = {
        "triggerContext": {
            "trigger": "comment_created",
            "newStatus": "to research",
            "title": "Improve debug signal",
        }
    }

    assert update_title(payload) == {"updatedTitle": "Improve debug signal"}


def test_no_duplicate_prefix_when_already_prefixed() -> None:
    payload = {
        "triggerContext": {
            "trigger": "status changed",
            "newStatus": "to_research",
            "title": "Cursor researching - Improve debug signal",
        }
    }

    assert update_title(payload) == {
        "updatedTitle": "Cursor researching - Improve debug signal"
    }


def test_direct_payload_is_supported() -> None:
    payload = {
        "trigger": "status_changed",
        "newStatus": "to research",
        "title": "Need technical validation",
    }

    assert update_title(payload) == {
        "updatedTitle": "Cursor researching - Need technical validation"
    }


def test_cli_reads_json_from_stdin() -> None:
    script = Path(__file__).resolve().parent / "linear_issue_title.py"
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "CLI example",
        }
    }

    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(completed.stdout) == {
        "updatedTitle": "Cursor researching - CLI example"
    }
