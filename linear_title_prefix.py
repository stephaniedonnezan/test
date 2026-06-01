"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WHITESPACE = re.compile(r"\s+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for to-research transitions."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_walk_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize_text(_new_status(contexts)) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _walk_contexts(
    value: Any,
    path: tuple[str, ...] = (),
    seen: set[int] | None = None,
) -> list[tuple[tuple[str, ...], Mapping[str, Any]]]:
    if seen is None:
        seen = set()

    if not isinstance(value, Mapping):
        return []

    value_id = id(value)
    if value_id in seen:
        return []
    seen.add(value_id)

    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]] = [(path, value)]
    for key, child in value.items():
        if isinstance(key, str) and isinstance(child, Mapping):
            contexts.extend(_walk_contexts(child, (*path, key), seen))
        elif isinstance(child, list):
            for index, item in enumerate(child):
                if isinstance(item, Mapping):
                    contexts.extend(_walk_contexts(item, (*path, key, str(index)), seen))

    return contexts


def _is_status_change_event(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
) -> bool:
    if _has_direct_status_change_trigger(contexts):
        return True

    return _has_issue_update_trigger(contexts) and _updated_fields_include_status(contexts)


def _has_direct_status_change_trigger(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
) -> bool:
    for _, context in contexts:
        for key in ("trigger", "webhookType", "eventType", "type"):
            normalized = _normalize_text(context.get(key))
            if not normalized:
                continue
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True
            if "status" in normalized and (
                "change" in normalized or "changed" in normalized
            ):
                return True
            if "state" in normalized and (
                "change" in normalized or "changed" in normalized
            ):
                return True

    return False


def _has_issue_update_trigger(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
) -> bool:
    for _, context in contexts:
        for key in ("trigger", "webhookType", "eventType", "action", "type"):
            normalized = _normalize_text(context.get(key))
            if not normalized:
                continue
            if normalized in {"update", "updated", "issue update", "issue updated"}:
                return True
            if "issue" in normalized and ("update" in normalized or "updated" in normalized):
                return True

    return False


def _updated_fields_include_status(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
) -> bool:
    for _, context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in {
            "status",
            "state",
            "workflow state",
            "workflow status",
        }

    if isinstance(value, Mapping):
        for key, child in value.items():
            if _contains_status_field(key) or _contains_status_field(child):
                return True
        return False

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for key in explicit_keys:
        status = _first_named_value(contexts, key)
        if status:
            return status

    for key in fallback_keys:
        status = _first_named_value(contexts, key)
        if status:
            return status

    return None


def _first_named_value(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
    key: str,
) -> str | None:
    for _, context in contexts:
        value = _value_name(context.get(key))
        if value:
            return value

    return None


def _value_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "display_name"):
            named = _value_name(value.get(key))
            if named:
                return named

    return None


def _issue_id(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier"):
        issue_id = _first_string(contexts, key)
        if issue_id:
            return issue_id

    issue_contexts = [
        (path, context)
        for path, context in contexts
        if "issue" in path or ("title" in context and _has_issue_status_metadata(context))
    ]
    for _, context in issue_contexts:
        issue_id = _clean_string(context.get("id"))
        if issue_id:
            return issue_id

    for path, context in contexts:
        if not path and "automationId" in context:
            continue
        issue_id = _clean_string(context.get("id"))
        if issue_id:
            return issue_id

    return None


def _issue_title(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    title = _first_string(contexts, "title")
    if title:
        return title

    return None


def _has_issue_status_metadata(context: Mapping[str, Any]) -> bool:
    return any(
        key in context
        for key in (
            "trigger",
            "webhookType",
            "eventType",
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
        )
    )


def _first_string(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
    key: str,
) -> str | None:
    for _, context in contexts:
        value = _clean_string(context.get(key))
        if value:
            return value

    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = _CAMEL_CASE_BOUNDARY.sub(" ", value.strip())
    spaced = spaced.replace("_", " ").replace("-", " ")
    return _WHITESPACE.sub(" ", spaced).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
