"""Build issue title updates for Linear "to research" status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The Cursor automation trigger uses a flat ``triggerContext`` payload, while
    Linear webhooks often nest issue data under ``data.issue``. This function
    accepts both shapes and returns a serializable action for the caller to send
    to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_token(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event
    yield from _nested_contexts(event, ("triggerContext", "payload", "data", "issue", "node"))


def _nested_contexts(
    value: Mapping[str, Any], keys: tuple[str, ...], seen: set[int] | None = None
) -> Iterable[Mapping[str, Any]]:
    if seen is None:
        seen = set()
    if id(value) in seen:
        return
    seen.add(id(value))

    for key in keys:
        nested = value.get(key)
        if isinstance(nested, Mapping):
            yield nested
            yield from _nested_contexts(nested, keys, seen)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            token = _normalize_event_name(context.get(key))
            if token in {"statuschanged", "statechanged", "workflowstatechanged"}:
                return True

    return _is_generic_issue_update(contexts) and _has_status_changed_field(contexts)


def _is_generic_issue_update(contexts: list[Mapping[str, Any]]) -> bool:
    update_tokens = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            if _normalize_event_name(context.get(key)) in update_tokens:
                return True
    return False


def _has_status_changed_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
        ):
            if _contains_status_field(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_status_field(key):
                return True
            if key in {"field", "fieldName", "name", "key", "property"} and _is_status_field(nested):
                return True
            if _contains_status_field(nested):
                return True
        return False

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in STATUS_FIELD_NAMES


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _new_status_from_change_metadata(context)
        if status:
            return status

    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ):
            status = _coerce_status(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_status(context.get(key))
            if status:
                return status

    return None


def _new_status_from_change_metadata(context: Mapping[str, Any]) -> str | None:
    for key in (
        "changes",
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
    ):
        status = _new_status_from_change_value(context.get(key))
        if status:
            return status
    return None


def _new_status_from_change_value(value: Any, field_name: str | None = None) -> str | None:
    if isinstance(value, Mapping):
        if field_name and _is_status_field(field_name):
            status = _coerce_status_from_keys(
                value,
                (
                    "newValue",
                    "new_value",
                    "to",
                    "after",
                    "value",
                    "name",
                    "status",
                    "state",
                    "workflowState",
                ),
            )
            if status:
                return status

        explicit_field = _coerce_status_from_keys(
            value, ("field", "fieldName", "field_name", "key", "property", "name")
        )
        field_is_status = _is_status_field(explicit_field)
        if field_is_status:
            status = _coerce_status_from_keys(
                value,
                ("newValue", "new_value", "to", "after", "value", "status", "state"),
            )
            if status and not _is_status_field(status):
                return status

        for key, nested in value.items():
            nested_status = _new_status_from_change_value(nested, str(key))
            if nested_status:
                return nested_status
        return None

    if isinstance(value, list | tuple):
        for item in value:
            status = _new_status_from_change_value(item, field_name)
            if status:
                return status

    return None


def _coerce_status_from_keys(value: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        status = _coerce_status(value.get(key))
        if status:
            return status
    return None


def _coerce_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "status", "state"):
            status = _coerce_status(value.get(key))
            if status:
                return status

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    issue_contexts = list(_issue_contexts(event))
    for context in issue_contexts:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _find_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("payload", "data", "issue"),
        ("payload", "issue"),
        ("data",),
        (),
    ):
        context: Any = event
        for key in path:
            if not isinstance(context, Mapping):
                context = None
                break
            context = context.get(key)
        if isinstance(context, Mapping):
            yield context


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_event_name(value: Any) -> str:
    return _normalize_token(value).replace(" ", "")


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    separated = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return " ".join(separated.lower().split())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
