"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    status = _new_status(mappings)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(mappings, ("title", "name"))
    issue_id = _first_text(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_mappings(value: Any) -> Sequence[Mapping[str, Any]]:
    """Yield mapping nodes from outermost to innermost for common payload shapes."""

    mappings: list[Mapping[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            mappings.append(node)
            for child in node.values():
                if isinstance(child, (Mapping, list, tuple)):
                    visit(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child)

    visit(value)
    return mappings


def _is_status_change_event(mappings: Sequence[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("trigger", "event", "eventType", "action", "type"):
            normalized = _normalize(mapping.get(key))
            if normalized in {"status changed", "status change", "state changed"}:
                return True
            if normalized in {"update", "updated", "issue updated", "updated issue"}:
                if _updated_status_fields(mappings):
                    return True
    return False


def _updated_status_fields(mappings: Sequence[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields"):
            fields = mapping.get(key)
            if _contains_status_field(fields):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_status_key(key) for key in changes):
            return True
        if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping) and _contains_status_field(
                    change.get("field") or change.get("name") or change.get("key")
                ):
                    return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _status_key(value)
    if isinstance(value, Mapping):
        return any(_status_key(key) or _contains_status_field(child) for key, child in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_key(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized is not None and normalized.replace(" ", "") in STATUS_FIELDS


def _new_status(mappings: Sequence[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _first_status_value(mappings, key)
        if value:
            return value

    for mapping in mappings:
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            value = _status_change_value(changes)
            if value:
                return value
        if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                if not _contains_status_field(change.get("field") or change.get("name") or change.get("key")):
                    continue
                value = _text_from_nested(change.get("newValue") or change.get("new_value") or change.get("to"))
                if value:
                    return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_status_value(mappings, key)
        if value:
            return value
    return None


def _status_change_value(changes: Mapping[str, Any]) -> str | None:
    for key, value in changes.items():
        if not _status_key(key):
            continue
        if isinstance(value, Mapping):
            return _text_from_nested(value.get("newValue") or value.get("new_value") or value.get("to") or value)
        return _text_from_nested(value)
    return None


def _first_status_value(mappings: Sequence[Mapping[str, Any]], key: str) -> str | None:
    for mapping in mappings:
        if key not in mapping:
            continue
        value = _text_from_nested(mapping[key])
        if value:
            return value
    return None


def _first_text(mappings: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _text_from_nested(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        return None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).lower()
    normalized = " ".join(value.split())
    return normalized or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
