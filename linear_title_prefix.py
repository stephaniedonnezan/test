"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation payloads can be either a flat Cursor trigger context or a
    nested Linear webhook-like object. The returned value is intentionally
    side-effect free so callers can decide how to apply the update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_string(contexts, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    for context in list(contexts):
        add(context.get("triggerContext"))
        add(context.get("data"))
        add(context.get("issue"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = _values_for_keys(
        contexts,
        (
            "trigger",
            "webhookType",
            "webhook_type",
            "action",
            "type",
            "eventType",
            "event_type",
        ),
    )
    normalized_triggers = {_normalize(value) for value in trigger_values}

    if any("status changed" in trigger or "status change" in trigger for trigger in normalized_triggers):
        return True

    if _updated_status_fields(contexts):
        return any(
            trigger in {"update", "updated", "issue update", "issue updated", "updated issue"}
            for trigger in normalized_triggers
        )

    return False


def _updated_status_fields(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("updatedFrom", "updated_from", "changes"):
            value = context.get(key)
            if isinstance(value, Mapping) and _contains_status_field(value.keys()):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        fields: Iterable[Any] = (value,)
    elif isinstance(value, Mapping):
        fields = value.keys()
    elif isinstance(value, Iterable):
        fields = value
    else:
        return False

    for field in fields:
        normalized = _normalize(str(field)).replace(" ", "")
        if normalized in {name.replace(" ", "") for name in STATUS_FIELD_NAMES}:
            return True
    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _extract_first_string(
        contexts,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "workflowStatus",
            "workflow_status",
        ),
    )
    if explicit:
        return explicit

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _string_or_name(context.get(key))
            if value:
                return value
    return None


def _extract_first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_or_name(context.get(key))
            if value and value.strip():
                return value
    return None


def _values_for_keys(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            value = _string_or_name(context.get(key))
            if value:
                values.append(value)
    return values


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", with_spaces).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
