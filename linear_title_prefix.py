"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
}
_DIRECT_STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to the research state.

    The automation runtime can send a flat Cursor triggerContext payload, while
    Linear webhooks often nest issue data under data/issue. This function keeps
    the public behavior small: it emits an update only for status-change events
    whose new status normalizes to "to research".
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts, event):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(RESEARCH_TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload contexts from most automation-specific to generic."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    yield event

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]], event: Mapping[str, Any]) -> bool:
    event_tokens = {
        _normalize_token(value)
        for context in contexts
        for key, value in context.items()
        if _normalize_key(key) in {"trigger", "triggertype", "webhooktype", "action", "type"}
        and isinstance(value, str)
    }

    if any(status_token in token for token in event_tokens for status_token in _DIRECT_STATUS_CHANGE_TOKENS):
        return True

    if event_tokens.intersection(_UPDATE_TOKENS) and _has_status_changed_field(event):
        return True

    return False


def _has_status_changed_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        changed_fields = payload.get(key)
        if isinstance(changed_fields, Iterable) and not isinstance(changed_fields, (str, bytes, Mapping)):
            if any(_is_status_field(field) for field in changed_fields):
                return True

    for key in ("changes", "updatedFrom", "updated_from"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
            return True

    data = payload.get("data")
    if isinstance(data, Mapping) and _has_status_changed_field(data):
        return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    status = _extract_status_value(contexts, explicit_status_keys)
    if status:
        return status

    return _extract_status_value(contexts, ("status", "state", "workflowState", "workflow_state"))


def _extract_status_value(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        normalized_key = _normalize_key(key)
        for context in contexts:
            for candidate_key, value in context.items():
                if _normalize_key(candidate_key) == normalized_key:
                    status = _coerce_name(value)
                    if status:
                        return status
    return None


def _extract_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        normalized_key = _normalize_key(key)
        for context in contexts:
            for candidate_key, value in context.items():
                if _normalize_key(candidate_key) == normalized_key and isinstance(value, str):
                    stripped = value.strip()
                    if stripped:
                        return stripped
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = _normalize_key(value)
    return normalized in _STATUS_FIELD_KEYS or normalized.endswith("status")


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = _split_camel_case(value)
    words = re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).casefold())


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).casefold())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
