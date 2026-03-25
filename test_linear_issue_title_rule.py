from linear_issue_title_rule import (
    RESEARCH_PREFIX,
    should_mark_as_researching,
    title_with_research_prefix,
    updated_title_from_payload,
)


def test_should_mark_as_researching_true_for_status_changed_to_research():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Fix swagger upload",
        }
    }
    assert should_mark_as_researching(payload) is True


def test_should_mark_as_researching_false_for_other_status():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "Done",
            "title": "Fix swagger upload",
        }
    }
    assert should_mark_as_researching(payload) is False


def test_title_with_research_prefix_adds_prefix():
    assert title_with_research_prefix("Fix swagger upload") == (
        f"{RESEARCH_PREFIX} - Fix swagger upload"
    )


def test_title_with_research_prefix_does_not_duplicate_prefix():
    original = f"{RESEARCH_PREFIX} - Fix swagger upload"
    assert title_with_research_prefix(original) == original


def test_updated_title_from_payload_returns_prefixed_title():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "[]QA - fix swagger",
        }
    }
    assert updated_title_from_payload(payload) == (
        f"{RESEARCH_PREFIX} - []QA - fix swagger"
    )


def test_updated_title_from_payload_returns_none_when_not_matching():
    payload = {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "In progress",
            "title": "[]QA - fix swagger",
        }
    }
    assert updated_title_from_payload(payload) is None
