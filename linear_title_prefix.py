"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_TOKENS = {
    "issueupdate",
    "issueupdated",
    "updateissue",
    "updatedissue",
    "update",
    "updated",
}
_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation trigger payload is intentionally accepted alongside
    common Linear webhook shapes so this logic can be reused in tests or a thin
    runtime adapter.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event.get("issue"))

    payload = event.get("payload")
    add(payload)
    if isinstance(payload, Mapping):
        add(payload.get("issue"))
        payload_data = payload.get("data")
        add(payload_data)
        if isinstance(payload_data, Mapping):
            add(payload_data.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    event_tokens = {
        _normalize_token(value)
        for context in context_list
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type")
        for value in (context.get(key),)
        if _is_scalar(value)
    }

    if event_tokens & _DIRECT_STATUS_CHANGE_TOKENS:
        return True

    if event_tokens & _GENERIC_UPDATE_TOKENS and _has_status_updated_field(context_list):
        return True

    return False


def _has_status_updated_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_token(key) in _STATUS_FIELD_TOKENS for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_TOKENS

    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        return _contains_status_field(field)

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = _text_value(context.get(key))
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            nested = _text_value(value.get(key))
            if nested:
                return nested
        return None

    if _is_scalar(value):
        text = str(value).strip()
        return text or None

    return None


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_words(value: Any) -> str | None:
    text = _text_value(value)
    if text is None:
        return None
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def _normalize_token(value: Any) -> str:
    words = _normalize_words(value)
    return "" if words is None else words.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
