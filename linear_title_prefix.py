"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _payload_candidates(event)
    if not _is_status_change_event(candidates):
        return None

    if _normalize_words(_new_status(candidates)) != TARGET_STATUS:
        return None

    issue_id = _issue_id(candidates)
    title = _issue_title(candidates)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return issue and trigger dictionaries in precedence order."""
    paths = [
        ("triggerContext",),
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        (),
        ("issue",),
        ("triggerContext", "issue"),
        ("automation_trigger_info", "triggerContext", "issue"),
        ("automationTriggerInfo", "triggerContext", "issue"),
        ("data", "issue"),
        ("payload", "data", "issue"),
        ("payload", "issue"),
        ("data",),
        ("payload", "data"),
        ("payload",),
    ]

    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for path in paths:
        value: Any = event
        for key in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(key)
        if isinstance(value, Mapping) and id(value) not in seen:
            candidates.append(value)
            seen.add(id(value))
    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_trigger(candidates):
        return True
    return _has_issue_update_trigger(candidates) and _has_status_change_metadata(candidates)


def _has_direct_status_change_trigger(candidates: list[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = _normalize_words(payload.get(key))
            if value in {
                "status changed",
                "status change",
                "issue status changed",
                "state changed",
                "workflow state changed",
            }:
                return True
    return False


def _has_issue_update_trigger(candidates: list[Mapping[str, Any]]) -> bool:
    for payload in candidates:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = _normalize_words(payload.get(key))
            if value in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _has_status_change_metadata(candidates: list[Mapping[str, Any]]) -> bool:
    change_keys = {
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changedProperties",
        "updatedProperties",
        "changes",
    }
    for payload in candidates:
        for key in change_keys:
            if key in payload and _contains_status_field(payload[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_words(key) in STATUS_FIELDS or _contains_status_field(child):
                return True
        return False
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "targetStatus",
        "target_status",
    )
    for payload in candidates:
        for key in explicit_keys:
            status = _coerce_name(payload.get(key))
            if status:
                return status

    for payload in candidates:
        for key in ("changes", "statusChange", "stateChange", "workflowStateChange"):
            status = _status_from_change(payload.get(key))
            if status:
                return status

    for payload in candidates:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_name(payload.get(key))
            if status:
                return status
    return None


def _status_from_change(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for status_key in ("status", "state", "workflowState", "workflow_state"):
        if status_key in value:
            status = _status_from_change(value[status_key]) or _coerce_name(value[status_key])
            if status:
                return status

    for key in ("to", "new", "after", "newValue", "new_value", "toValue", "to_value"):
        status = _coerce_name(value.get(key))
        if status:
            return status
    return None


def _issue_id(candidates: list[Mapping[str, Any]]) -> str | None:
    preferred_keys = ("issueId", "issue_id", "identifier", "key")
    for payload in candidates:
        for key in preferred_keys:
            issue_id = _coerce_name(payload.get(key))
            if issue_id:
                return issue_id

    for payload in candidates:
        if "title" not in payload:
            continue
        issue_id = _coerce_name(payload.get("id"))
        if issue_id:
            return issue_id
    return None


def _issue_title(candidates: list[Mapping[str, Any]]) -> str | None:
    for payload in candidates:
        title = _coerce_name(payload.get("title"))
        if title:
            return title
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            name = _coerce_name(value.get(key))
            if name:
                return name
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    text = _coerce_name(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True) if update else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
