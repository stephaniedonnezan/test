"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation runtime can pass either the flat Cursor trigger context or a
    nested Linear webhook payload. This function keeps the decision local and
    side-effect free so the caller can perform the actual Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_ordered_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from most to least specific."""

    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from emit(event.get("triggerContext"))
    yield from emit(event)
    yield from emit(event.get("data"))
    yield from emit(_mapping_at(event, ("data", "issue")))
    yield from emit(event.get("issue"))
    yield from emit(_mapping_at(event, ("payload", "issue")))
    yield from emit(event.get("payload"))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    contexts = list(contexts)

    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_words(value))

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    has_issue_update = any(value in _ISSUE_UPDATE_TRIGGERS for value in trigger_values)
    return has_issue_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            if _value_mentions_status_field(context.get(key)):
                return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field_name(str(key)) or _value_mentions_status_field(nested_value):
                return True
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if _value_mentions_status_field(item):
                return True
    return False


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for context in contexts:
        status = _status_from_explicit_keys(
            context,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
            ),
        )
        if status:
            return status

    for context in contexts:
        status = _status_from_change_sets(context)
        if status:
            return status

    for context in contexts:
        status = _status_from_explicit_keys(
            context,
            (
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        if status:
            return status

    return None


def _status_from_explicit_keys(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        status = _status_text(context.get(key))
        if status:
            return status
    return None


def _status_from_change_sets(context: Mapping[str, Any]) -> str | None:
    for key in ("changes", "change", "updatedFields", "updated_fields"):
        value = context.get(key)
        if not isinstance(value, Mapping):
            continue

        for field_name, change in value.items():
            if not _is_status_field_name(str(field_name)):
                continue

            status = _status_text(change)
            if status:
                return status

            if isinstance(change, Mapping):
                status = _status_from_explicit_keys(
                    change,
                    ("to", "new", "after", "toStatus", "newStatus", "name"),
                )
                if status:
                    return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "value", "label", "title"):
            text = _status_text(value.get(key))
            if text:
                return text

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping_at(context: Mapping[str, Any], keys: Iterable[str]) -> Mapping[str, Any] | None:
    value: Any = context
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _is_status_field_name(value: str) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action:
        json.dump(action, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
