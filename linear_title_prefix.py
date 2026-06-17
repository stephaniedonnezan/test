"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_MARKERS = ("status", "state", "workflow state", "workflowstate")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_event_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue containers from flat or nested webhooks."""
    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from add(event)

    for key in ("triggerContext", "payload", "data", "issue", "node"):
        value = event.get(key)
        yield from add(value)

        if isinstance(value, Mapping):
            for nested_key in ("triggerContext", "payload", "data", "issue", "node", "state", "status", "workflowState"):
                yield from add(value.get(nested_key))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)

    trigger_values = []
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "event", "eventType"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(value in {"update", "updated", "issue update", "issue updated", "updated issue"} for value in trigger_values):
        return _has_changed_status_field(contexts)

    return False


def _is_direct_status_change(value: str) -> bool:
    return value in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _field_collection_mentions_status(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                return True
            if isinstance(item, Mapping):
                field = _extract_first_text((item,), ("field", "name", "key", "id"))
                if field and _is_status_field(field):
                    return True

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    return any(marker in normalized for marker in STATUS_FIELD_MARKERS)


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    changed_status = _extract_status_from_change_metadata(contexts)
    if changed_status:
        return changed_status

    explicit_status = _extract_first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "newState",
            "new_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status:
        return explicit_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, Mapping):
                name = _extract_first_text((value,), ("name", "title", "label"))
                if name:
                    return name

    return None


def _extract_status_from_change_metadata(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changedFields"):
            value = context.get(key)
            status = _extract_status_from_change_value(value)
            if status:
                return status

    return None


def _extract_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field, change in value.items():
            if _is_status_field(field):
                status = _extract_change_target(change)
                if status:
                    return status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field = _extract_first_text((item,), ("field", "name", "key", "id"))
            if field and _is_status_field(field):
                status = _extract_change_target(item)
                if status:
                    return status

    return None


def _extract_change_target(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()

    if not isinstance(value, Mapping):
        return None

    target = _extract_first_text(
        (value,),
        ("to", "new", "after", "value", "current", "newValue", "currentValue"),
    )
    if target:
        return target

    for key in ("to", "new", "after", "value", "current", "newValue", "currentValue"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            target = _extract_first_text((nested,), ("name", "title", "label"))
            if target:
                return target

    return None


def _extract_first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _coerce_text(value)
            if text:
                return text

    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        return _extract_first_text((value,), ("name", "title", "label"))

    return None


def _normalize_text(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read a JSON event from stdin and print the title-update action, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
