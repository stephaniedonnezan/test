"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation runtime is expected to perform the actual Linear API update.
    This function only decides whether an incoming webhook payload requires the
    title change and builds a small action object for the caller.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _extract_issue_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _first_text(
        event,
        payload,
        keys=("newStatus", "new_status", "status", "state", "workflowState"),
    )
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(
        event,
        payload,
        keys=("id", "issueId", "issue_id", "identifier"),
    )
    title = _first_text(event, payload, keys=("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _extract_issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Merge common Linear nesting shapes while preserving top-level overrides."""

    merged: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                merged.update(nested_issue)

    merged.update(event)
    return merged


def _is_status_change(
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    trigger = _first_text(
        event,
        payload,
        keys=("trigger", "webhookType", "action", "type"),
    )
    normalized_trigger = _normalize_text(trigger)
    if normalized_trigger in {"status changed", "status change", "statuschanged"}:
        return True

    if normalized_trigger in {"issue updated", "updated issue", "issue update"}:
        return _updated_fields_include_status(event) or _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields")
    if fields is None:
        fields = payload.get("updated_fields")
    if fields is None:
        fields = payload.get("changes")

    if isinstance(fields, str):
        candidates = [fields]
    elif isinstance(fields, Mapping):
        candidates = list(fields.keys())
    elif isinstance(fields, (list, tuple, set)):
        candidates = list(fields)
    else:
        return False

    return any(_normalize_text(_stringify(candidate)) in {"status", "state"} for candidate in candidates)


def _first_text(
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    keys: tuple[str, ...],
) -> str | None:
    for source in (event, payload):
        value = _nested_lookup(source, keys)
        text = _stringify(value)
        if text:
            return text
    return None


def _nested_lookup(source: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in source:
            value = source[key]
            if isinstance(value, Mapping):
                for nested_key in ("name", "title", "id", "identifier"):
                    if nested_key in value:
                        return value[nested_key]
            return value
    return None


def _stringify(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
