"""Build Linear issue-title updates for research status changes.

The automation receives slightly different payload shapes depending on whether
Cursor or Linear emitted the webhook.  This module keeps the behavior small and
predictable: only status changes into "to research" receive the title marker.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event should be marked."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change(contexts):
        return None

    if _normalize_status(_extract_new_status(contexts)) != TARGET_STATUS:
        return None

    title = _extract_issue_title(contexts)
    issue_id = _extract_issue_id(contexts)
    if not title or not issue_id:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful mappings from outer metadata through nested issue payloads."""

    yielded: list[int] = []

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping):
            identity = id(value)
            if identity not in yielded:
                yielded.append(identity)
                yield value

    # Prefer trigger context and nested issue data before the wrapper event.  A
    # wrapper can contain automation-level ids that are not Linear issue ids.
    yield from emit(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        yield from emit(data.get("issue"))
        yield from emit(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield from emit(issue)

    payload = event.get("payload")
    if isinstance(payload, Mapping):
        yield from emit(payload.get("issue"))
        yield from emit(payload)

    yield from emit(event)


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for context in contexts
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
        if (value := context.get(key)) is not None
    ]

    if any(
        ("status" in value or "state" in value) and "chang" in value
        for value in trigger_values
    ):
        return True

    if any("update" in value or "updated" in value for value in trigger_values):
        return _changed_fields_include_status(contexts)

    return False


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping):
                if any(_is_status_field(field) for field in value):
                    return True
            elif _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_field_name(value)
    return normalized in STATUS_CHANGE_FIELDS or normalized.endswith("status")


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        direct = _first_text(
            context,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "targetStatus",
                "target_status",
            ),
        )
        if direct:
            return direct

    for context in contexts:
        for key in ("changes", "changed"):
            changed_status = _status_from_changes(context.get(key))
            if changed_status:
                return changed_status

    for context in contexts:
        fallback = _first_text(context, ("status",))
        if fallback:
            return fallback

        for key in ("state", "workflowState", "workflow_state"):
            nested = _nested_text(context.get(key), ("name", "title", "status"))
            if nested:
                return nested

    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if not _is_status_field(key):
            continue

        if isinstance(change, Mapping):
            new_value = _first_text(change, ("to", "new", "newValue", "after"))
            if new_value:
                return new_value
            nested_name = _nested_text(change.get("to"), ("name", "title"))
            if nested_name:
                return nested_name

        if isinstance(change, str):
            return change

    return None


def _extract_issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = _first_text(context, ("title", "name"))
        if title:
            return title
    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        issue_id = _first_text(
            context,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
        if issue_id:
            return issue_id
    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _clean_text(context.get(key))
        if value:
            return value
    return None


def _nested_text(value: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, keys)
    return _clean_text(value)


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, (int, float)):
        return str(value)

    return None


def _normalize_status(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None

    return re.sub(r"\s+", " ", _split_words(cleaned)).casefold()


def _normalize_token(value: Any) -> str:
    cleaned = _clean_text(value)
    if cleaned is None:
        return ""

    return re.sub(r"\s+", "", _split_words(cleaned)).casefold()


def _normalize_field_name(value: Any) -> str:
    cleaned = _clean_text(value)
    if cleaned is None:
        return ""

    return re.sub(r"\s+", " ", _split_words(cleaned)).casefold()


def _split_words(value: str) -> str:
    with_camel_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^A-Za-z0-9]+", " ", with_camel_boundaries).strip()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
