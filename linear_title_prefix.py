"""Build Linear issue title updates for to-research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The function is intentionally side-effect free: automation runners can pass
    the returned action to their Linear client, while unrelated events return
    ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_maps(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _issue_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _normalize(clean_title).startswith(_normalize(TITLE_PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation hooks named after the trigger."""

    return build_issue_title_update(event)


def _context_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload contexts from most issue-specific to most global."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    for container in (event.get("triggerContext"), event.get("data"), event.get("issue")):
        if isinstance(container, Mapping):
            add(container.get("issue"))
            add(container.get("data"))
            add(container)

    add(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "type", "action"):
            normalized = _normalize(context.get(key))
            if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if normalized in _ISSUE_UPDATE_EVENTS:
                saw_issue_update = True

    return saw_issue_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "updatedFrom"):
            raw_fields = context.get(key)
            if isinstance(raw_fields, str):
                fields: Iterable[Any] = (raw_fields,)
            elif isinstance(raw_fields, Mapping):
                fields = raw_fields.keys()
            elif isinstance(raw_fields, Iterable) and not isinstance(raw_fields, bytes):
                fields = raw_fields
            else:
                continue

            for field in fields:
                field_name = _field_name(field)
                if _normalize(field_name) in _STATUS_FIELD_NAMES:
                    return True

    return False


def _field_name(field: Any) -> str:
    if isinstance(field, Mapping):
        return _first_text((field,), ("field", "name", "key", "id")) or ""
    return str(field)


def _issue_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                nested_status = _first_text((value,), ("name", "title", "label"))
                if nested_status:
                    return nested_status

    return None


def _issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_text(contexts, ("issueId", "issue_id", "id", "identifier"))


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the title-update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
