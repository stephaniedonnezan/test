import json

from linear_issue_title import PREFIX, update_issue_title


def test_prefixes_title_on_to_research_status_change():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "[625]Error reports through API",
        }
    }

    assert update_issue_title(payload) == f"{PREFIX} - [625]Error reports through API"


def test_does_not_change_title_for_other_status():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "Canceled",
            "title": "[625]Error reports through API",
        }
    }

    assert update_issue_title(payload) == "[625]Error reports through API"


def test_does_not_change_title_for_other_trigger():
    payload = {
        "triggerContext": {
            "trigger": "issue_created",
            "newStatus": "to research",
            "title": "[625]Error reports through API",
        }
    }

    assert update_issue_title(payload) == "[625]Error reports through API"


def test_does_not_duplicate_prefix():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Cursor researching - [625]Error reports through API",
        }
    }

    assert update_issue_title(payload) == "Cursor researching - [625]Error reports through API"


def test_supports_root_level_payload():
    payload = {
        "trigger": "status_changed",
        "newStatus": "to research",
        "title": "Error reports through API",
    }

    assert update_issue_title(payload) == "Cursor researching - Error reports through API"


def test_cli_output_from_payload_shape():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Error reports through API",
        }
    }
    expected = {"updatedTitle": "Cursor researching - Error reports through API"}

    assert json.loads(json.dumps({"updatedTitle": update_issue_title(payload)})) == expected
