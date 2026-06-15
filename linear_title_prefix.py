"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_collect_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Collect likely envelope and issue payload mappings with outer values first."""

    contexts: list[Mapping[str, Any]] = []

    def visit(candidate: Any) -> None:
        if not isinstance(candidate, Mapping) or candidate in contexts:
            return

        contexts.append(candidate)
        for key in ("triggerContext", "data", "issue", "state", "status", "workflowState"):
            visit(candidate.get(key))

    visit(value)
    return tuple(contexts)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            value = _as_text(context.get(key))
            normalized = _normalize(value)
            if not normalized:
                continue
            if "status" in normalized and any(
                verb in normalized for verb in ("changed", "change")
            ):
                return True
            if normalized in {"status changed", "status updated"}:
                return True

    return _updated_status_fields(contexts)


def _updated_status_fields(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            raw_fields = context.get(key)
            fields = raw_fields if isinstance(raw_fields, (list, tuple, set)) else [raw_fields]
            for field in fields:
                if _field_name(field) in STATUS_FIELDS:
                    return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _field_name(field) in STATUS_FIELDS:
                    return True
        elif isinstance(changes, list):
            for change in changes:
                if _field_name(change) in STATUS_FIELDS:
                    return True

    return False


def _field_name(field: Any) -> str:
    if isinstance(field, Mapping):
        field = field.get("field") or field.get("name") or field.get("key")
    return _normalize(field).replace(" ", "")


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            value = _nested_value(context, key)
            text = _as_text(value)
            if text and text.strip():
                return text
    return None


def _nested_value(context: Mapping[str, Any], key: str) -> Any:
    value = context.get(key)
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("id")
    return value


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        nested = value.get("name") or value.get("title") or value.get("id")
        return _as_text(nested)
    return str(value)


def _normalize(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _has_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
