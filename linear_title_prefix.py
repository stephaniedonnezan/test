"""Build Linear issue title updates for Cursor research-status automations.

The automation runner can pipe a Linear/Cursor webhook payload to this module.
When the issue status changes to "to research", the handler returns an action
that prefixes the issue title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The function is intentionally side-effect free. It accepts the flat
    ``triggerContext`` shape used by Cursor Automations as well as common nested
    Linear webhook payloads under ``data`` and ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_extract_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield relevant payload objects from outermost metadata to issue data."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        marker = id(value)
        if marker in seen:
            return
        seen.add(marker)

        yield value

        for key in (
            "automation_trigger_info",
            "automationTriggerInfo",
            "triggerContext",
            "trigger_context",
            "payload",
            "webhook",
            "data",
            "issue",
        ):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from visit(nested)

    yield from visit(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    """Detect direct status-change triggers and generic issue update payloads."""

    trigger_values: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _is_direct_status_change(value: str) -> bool:
    return "status" in value.split() and (
        "changed" in value.split() or "change" in value.split()
    )


def _is_issue_update(value: str) -> bool:
    words = set(value.split())
    return value == "update" or {"issue", "updated"} <= words or {"updated", "issue"} <= words


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_list_includes_status(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues", "previous_values"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(isinstance(field, str) and _is_status_field(field) for field in value)
    return False


def _is_status_field(value: Any) -> bool:
    return isinstance(value, str) and _normalize_text(value) in STATUS_FIELDS


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
    )
    fallback_keys = (
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )

    for context in contexts:
        value = _first_present(context, explicit_keys)
        if value is not None:
            return _named_value(value)

    for context in contexts:
        for key in ("changes", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                value = _status_from_changes(changes)
                if value is not None:
                    return value

    for context in contexts:
        value = _first_present(context, fallback_keys)
        if value is not None:
            return _named_value(value)

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> Any:
    for field, value in changes.items():
        if not _is_status_field(field):
            continue

        if isinstance(value, Mapping):
            for key in ("to", "new", "after", "current", "name"):
                if key in value:
                    return _named_value(value[key])
        return _named_value(value)

    return None


def _first_present(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return value


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = _normalize_text(value)
    return normalized or None


def _normalize_text(value: str) -> str:
    with_spaced_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_spaced_camel)
    return re.sub(r"\s+", " ", words_only).strip().casefold()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}))
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
