"""Build Linear issue title updates for research status changes.

The automation host is expected to call ``build_issue_title_update`` with the
Linear status-change payload and apply the returned action, if any.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The handler accepts both the flat Cursor automation trigger context shape and
    common nested Linear webhook shapes. It deliberately returns ``None`` for
    unrelated events so callers can safely run it for every issue webhook.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_find_status(event)) != TARGET_STATUS:
        return None

    issue_id = _find_string(event, ("id", "issueId", "issue_id", "identifier"))
    title = _find_string(event, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_event_name(value)
        for context in _contexts(event)
        for key, value in context.items()
        if key in {"trigger", "webhookType", "action", "type"}
    }

    if event_names & {"status changed", "status change", "status updated"}:
        return True

    if event_names & {"update", "updated", "issue updated", "updated issue"}:
        updated_fields = _updated_field_names(event)
        return bool(updated_fields & _STATUS_FIELD_NAMES)

    return False


def _updated_field_names(event: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()
    for context in _contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            fields.update(_field_names(value))
    return fields


def _field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_field_name(value)}

    if isinstance(value, Mapping):
        return {_normalize_field_name(key) for key in value.keys()}

    if isinstance(value, Iterable):
        names: set[str] = set()
        for item in value:
            if isinstance(item, str):
                names.add(_normalize_field_name(item))
            elif isinstance(item, Mapping):
                for key in ("name", "field", "key"):
                    item_value = item.get(key)
                    if isinstance(item_value, str):
                        names.add(_normalize_field_name(item_value))
        return names

    return set()


def _find_status(event: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState"):
        value = _find_value(event, (key,))
        if value is not None:
            return value

    for key in ("status", "state", "workflowState", "workflow_status"):
        value = _find_value(event, (key,))
        if value is not None:
            return value

    return None


def _find_string(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _find_value(event, keys)
    return value if isinstance(value, str) else None


def _find_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    key_set = set(keys)
    for context in _contexts(event):
        for key in keys:
            if key in context:
                return _extract_name(context[key])

        for context_key, value in context.items():
            if context_key in key_set:
                return _extract_name(value)

    return None


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                return nested_value
    return value


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _collect_contexts(event, contexts)
    return contexts


def _collect_contexts(value: Any, contexts: list[Mapping[str, Any]]) -> None:
    if not isinstance(value, Mapping):
        return

    contexts.append(value)
    for key in ("triggerContext", "data", "issue", "node", "object"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            _collect_contexts(nested, contexts)


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_words(value: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower()).split()
    )


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
