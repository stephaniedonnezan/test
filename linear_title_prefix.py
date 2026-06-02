"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TOKENS = {"statuschanged", "statuschange"}
_UPDATE_TOKENS = {"update", "issueupdated", "updatedissue"}
_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads):
        return None

    status = _new_status(payloads)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payloads, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload locations, preferring wrapper metadata over issue data."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event.get("triggerContext"))
    add(event)

    for container in list(candidates):
        add(container.get("data"))
        add(container.get("issue"))
        data = container.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))

    return candidates


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]]) -> bool:
    has_update_event = False

    for payload in payloads:
        for key in ("trigger", "event", "webhookType", "webhook_type", "action", "type"):
            token = _normalize_token(payload.get(key))
            if token in _STATUS_CHANGE_TOKENS:
                return True
            if token in _UPDATE_TOKENS:
                has_update_event = True

    return has_update_event and _updated_fields_include_status(payloads)


def _updated_fields_include_status(payloads: Iterable[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = payload.get(key)
            if _field_collection_includes_status(value):
                return True
    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_TOKENS
    if isinstance(value, Mapping):
        keys = set(value.keys())
        return any(_normalize_token(key) in _STATUS_FIELD_TOKENS for key in keys)
    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _new_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(payloads, _EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    for payload in payloads:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = _text(value.get("name")) or _text(value.get("title"))
                if name:
                    return name

    return None


def _first_text(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = _text(payload.get(key))
            if value:
                return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_words(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[A-Za-z0-9]+", spaced)
    return " ".join(word.lower() for word in words)


def _normalize_token(value: Any) -> str | None:
    words = _normalize_words(value)
    if words is None:
        return None
    return words.replace(" ", "")


def main() -> None:
    """Read a JSON event from stdin and print the title update action, if any."""

    result = build_issue_title_update(json.load(sys.stdin))
    if result is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
