"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The Cursor automation trigger payload is intentionally small, but Linear
    webhooks can nest issue fields under ``data`` or ``issue``. This function
    accepts both shapes and returns a side-effect-free action descriptor that
    callers can pass to their Linear update layer.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_text(_first_status(contexts)) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "issueTitle"))
    issue_id = _first_text(
        contexts,
        ("id", "issueId", "issue_id", "identifier", "issueIdentifier"),
    )
    if title is None or issue_id is None:
        return None

    normalized_title = title.strip()
    normalized_issue_id = issue_id.strip()
    if not normalized_title or not normalized_issue_id:
        return None

    if _has_research_prefix(normalized_title):
        next_title = normalized_title
    else:
        next_title = f"{TITLE_PREFIX}{TITLE_SEPARATOR}{normalized_title}"

    return {
        "action": "update_issue_title",
        "issueId": normalized_issue_id,
        "title": next_title,
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(event.get("issue"))
    add(data)
    add(event)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    direct_trigger = False
    issue_update = False
    status_field_updated = False

    for context in contexts:
        trigger_values = (
            context.get("trigger"),
            context.get("webhookType"),
            context.get("action"),
            context.get("type"),
        )
        for value in trigger_values:
            normalized = _normalize_text(value)
            if normalized in {"status changed", "status change", "status updated"}:
                direct_trigger = True
            if normalized in {"issue updated", "updated issue", "update", "updated"}:
                issue_update = True

        if _updated_fields_include_status(context.get("updatedFields")):
            status_field_updated = True
        if _updated_fields_include_status(context.get("updated_fields")):
            status_field_updated = True

    return direct_trigger or (issue_update and status_field_updated) or status_field_updated


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        values = value
    else:
        return False

    return any(
        _normalize_text(field) in {"status", "state", "workflow state", "workflow status"}
        for field in values
    )


def _first_text(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
) -> str | None:
    for key in keys:
        for context in contexts:
            value = _extract_key_path(context, key)
            if value is not None:
                return value
    return None


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "state.name",
            "workflowState.name",
        ),
    )


def _extract_key_path(context: Mapping[str, Any], key_path: str) -> str | None:
    current: Any = context
    for key in key_path.split("."):
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return _as_text(current)


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _as_text(value.get(key))
            if text is not None:
                return text
    return None


def _normalize_text(value: Any) -> str:
    text = _as_text(value)
    if text is None:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
