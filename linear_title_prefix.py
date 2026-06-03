"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The Cursor automation trigger payload is flat under ``triggerContext``, while
    Linear webhooks often nest issue fields under ``data`` or ``issue``. This
    function accepts both shapes and returns ``None`` for events that should not
    update an issue title.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue = _issue_context(contexts)
    issue_id = _clean_text(_first_value(issue, ("id", "issueId", "issue_id", "identifier", "uuid")))
    title = _clean_text(_first_value(issue, ("title", "name")))

    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload contexts from most specific metadata to issue data."""

    result: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "webhook", "payload", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            result.append(value)
            result.extend(_nested_contexts(value))
    return _unique_mappings(result)


def _nested_contexts(value: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "payload", "data", "issue", "state", "workflowState", "status"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            result.append(nested)
            result.extend(_nested_contexts(nested))
    return result


def _unique_mappings(values: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for value in values:
        value_id = id(value)
        if value_id not in seen:
            unique.append(value)
            seen.add(value_id)
    return unique


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_explicit_status_change_trigger(contexts):
        return True

    if not _has_issue_update_trigger(contexts):
        return False

    changed_fields = _changed_fields(contexts)
    status_fields = {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
        "workflowstatus",
    }
    return not changed_fields or any(field in status_fields for field in changed_fields)


def _has_explicit_status_change_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "event", "eventType", "type", "action"):
            normalized = _normalize_status(context.get(key))
            if normalized in {"status changed", "status change", "statuschanged"}:
                return True
    return False


def _has_issue_update_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "event", "eventType", "type", "action"):
            normalized = _normalize_status(context.get(key))
            if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _changed_fields(contexts: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            value = context.get(key)
            if isinstance(value, str):
                fields.add(_normalize_status(value))
            elif isinstance(value, list | tuple | set):
                fields.update(_normalize_status(item) for item in value)

        for key in ("updatedFrom", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping):
                fields.update(_normalize_status(field) for field in value.keys())
    return {field for field in fields if field}


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        value = _first_value(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if value is not None:
            return value

    for context in contexts:
        for key in ("state", "workflowState", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested = _first_value(value, ("name", "title", "status", "state"))
                if nested is not None:
                    return nested
            elif value is not None:
                return value
    return None


def _issue_context(contexts: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    for context in contexts:
        issue = context.get("issue")
        if isinstance(issue, Mapping) and _first_value(issue, ("title", "name")) is not None:
            return issue

    for context in contexts:
        data = context.get("data")
        if isinstance(data, Mapping):
            issue = data.get("issue")
            if isinstance(issue, Mapping) and _first_value(issue, ("title", "name")) is not None:
                return issue
            if _first_value(data, ("title", "name")) is not None:
                return data

    for context in contexts:
        if _first_value(context, ("title", "name")) is not None:
            return context
    return {}


def _first_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
