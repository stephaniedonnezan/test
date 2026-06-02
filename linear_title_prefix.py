"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event/issue dictionaries from most to least specific."""
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    data_issue = _as_mapping(data.get("issue")) if data else None
    issue = _as_mapping(event.get("issue"))

    for context in (trigger_context, data_issue, data, issue, event):
        if context is not None:
            yield context


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if any(_is_direct_status_changed(context) for context in contexts):
        return True

    if not any(_is_update_action(context) for context in contexts):
        return False

    return any(_updated_status_fields(context) for context in contexts)


def _is_direct_status_changed(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "action", "type", "event", "webhookType"):
        value = _as_text(context.get(key))
        if value and _normalize_text(value) == "status changed":
            return True
    return False


def _is_update_action(context: Mapping[str, Any]) -> bool:
    for key in ("action", "trigger", "type", "event"):
        value = _as_text(context.get(key))
        if not value:
            continue
        normalized = _normalize_text(value)
        if normalized in {"update", "updated", "issue updated", "updated issue"}:
            return True
    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(fields, Iterable):
            continue
        for field in fields:
            normalized = _normalize_key(_as_text(field))
            if normalized in STATUS_FIELDS:
                return True
    return False


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )
    return _extract_first_text(contexts, status_keys)


def _extract_first_text(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
) -> str | None:
    for context in contexts:
        for key in keys:
            value = _extract_value(context, key)
            text = _as_text(value)
            if text:
                return text
    return None


def _extract_value(context: Mapping[str, Any], key: str) -> Any:
    if key in context:
        value = context[key]
        if isinstance(value, Mapping):
            return value.get("name") or value.get("title") or value.get("id")
        return value

    normalized_key = _normalize_key(key)
    for candidate_key, value in context.items():
        if _normalize_key(_as_text(candidate_key)) != normalized_key:
            continue
        if isinstance(value, Mapping):
            return value.get("name") or value.get("title") or value.get("id")
        return value

    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _normalize_key(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-zA-Z0-9]+", "", value).casefold()


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
