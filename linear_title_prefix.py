"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "stateid",
    "state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The function intentionally has no side effects so it can be tested and used
    by whatever integration layer performs the actual Linear API update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_value(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload layers from most-specific issue data to wrappers."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)

        for key in ("triggerContext", "issue", "data", "node"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from visit(nested)

        yield value

    yield from visit(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_value(context.get(key))
            if normalized in {"status changed", "status change", "state changed", "workflow state changed"}:
                return True
            if normalized in {"issue updated", "updated issue", "update"}:
                return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _field_names_include_status(context.get(key)):
                return True

        changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
        if isinstance(changes, Mapping) and _field_names_include_status(changes.keys()):
            return True

    return False


def _field_names_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        field_names = [fields]
    elif isinstance(fields, Mapping):
        field_names = fields.keys()
    elif isinstance(fields, Iterable):
        field_names = fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in field_names)


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _extract_first_string(
            [context],
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
                "statusName",
                "status_name",
            ),
        )
        if value:
            return value

    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            value = _extract_changed_status(changes)
            if value:
                return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _string_value(context.get(key))
            if value:
                return value

    return None


def _extract_changed_status(changes: Mapping[str, Any]) -> str | None:
    for field_name, change in changes.items():
        if _normalize_field_name(field_name) not in STATUS_FIELD_NAMES:
            continue

        if isinstance(change, Mapping):
            value = _extract_first_string(
                [change],
                ("to", "new", "after", "name", "newValue", "new_value"),
            )
            if value:
                return value

        value = _string_value(change)
        if value:
            return value

    return None


def _extract_first_string(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = _string_value(value.get(key))
            if nested:
                return nested

    return None


def _normalize_value(value: Any) -> str:
    string = _string_value(value)
    if not string:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", string)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _normalize_field_name(value: Any) -> str:
    string = str(value)
    return re.sub(r"[^a-zA-Z0-9_]+", "", string).lower()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
