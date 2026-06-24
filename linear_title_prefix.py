"""Build Linear issue-title updates for Cursor research automations.

The automation receives webhook-like payloads from Cursor/Linear.  When an
issue status changes to "to research", callers can use the returned action to
update the issue title with a "Cursor researching" prefix.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
ACTION = "update_issue_title"

_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b\s*:?", re.IGNORECASE)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_DIRECT_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
_UPDATE_MARKERS = {"update", "updated", "issue update", "issue updated", "updated issue"}
_EVENT_KIND_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "updatedFrom",
    "updated_from",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The function is intentionally side-effect free: it validates the event and
    constructs the desired update, leaving the actual Linear API call to the
    automation runtime.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_status_from_event(event)) != "to research":
        return None

    title = _issue_title(event)
    issue_id = _issue_id(event)
    if not title or not issue_id:
        return None

    updated_title = _prefixed_title(title)
    if updated_title == title:
        return None

    return {"action": ACTION, "issueId": issue_id, "title": updated_title}


def derive_updated_title(event: Any) -> str | None:
    """Return only the updated title for callers that do not need metadata."""

    update = build_issue_title_update(event)
    if update is None:
        return None
    return update["title"]


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_kinds = [_normalize(value) for value in _event_kind_values(event)]

    if any(kind in _DIRECT_STATUS_CHANGE_MARKERS for kind in event_kinds):
        return True

    if any("status changed" in kind or "state changed" in kind for kind in event_kinds):
        return True

    is_generic_update = any(kind in _UPDATE_MARKERS for kind in event_kinds)
    return (is_generic_update or not event_kinds) and _has_status_field_change(event)


def _event_kind_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for source in _metadata_sources(event):
        for key in _EVENT_KIND_KEYS:
            if key in source:
                values.append(source[key])
    return values


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = [source for source in _roots(event) if isinstance(source, Mapping)]
    # The outer payload often carries trigger metadata around triggerContext.
    if event not in sources:
        sources.append(event)
    return _dedupe_mappings(sources)


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    for source in _metadata_sources(event):
        for key in _UPDATED_FIELD_KEYS:
            if key not in source:
                continue
            if _contains_status_field(source[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                return True
            if _contains_status_field(nested_value):
                return True
        return False
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_from_event(event: Mapping[str, Any]) -> Any:
    for source in _status_sources(event):
        for key in _NEW_STATUS_KEYS:
            if key in source:
                return source[key]

    changed_status = _status_from_change_records(event)
    if changed_status is not None:
        return changed_status

    for source in _status_sources(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in source:
                value = source[key]
                if isinstance(value, Mapping):
                    for name_key in ("name", "title", "value"):
                        if name_key in value:
                            return value[name_key]
                else:
                    return value
    return None


def _status_from_change_records(event: Mapping[str, Any]) -> Any:
    for source in _metadata_sources(event):
        for key in ("changes", "updatedFrom", "updated_from"):
            value = source.get(key)
            if not isinstance(value, Mapping):
                continue
            for field_name, change in value.items():
                if _normalize_field_name(field_name) not in _STATUS_FIELD_NAMES:
                    continue
                if isinstance(change, Mapping):
                    for value_key in ("to", "new", "newValue", "new_value", "name", "value"):
                        if value_key in change:
                            nested_value = change[value_key]
                            if isinstance(nested_value, Mapping):
                                for name_key in ("name", "title", "value"):
                                    if name_key in nested_value:
                                        return nested_value[name_key]
                            return nested_value
                return change
    return None


def _status_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for root in _roots(event):
        if not isinstance(root, Mapping):
            continue
        sources.append(root)
        data = root.get("data")
        if isinstance(data, Mapping):
            sources.append(data)
            issue = data.get("issue")
            if isinstance(issue, Mapping):
                sources.append(issue)
        issue = root.get("issue")
        if isinstance(issue, Mapping):
            sources.append(issue)
    return _dedupe_mappings(sources)


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for root in _roots(event):
        if not isinstance(root, Mapping):
            continue
        data = root.get("data")
        if isinstance(data, Mapping):
            issue = data.get("issue")
            if isinstance(issue, Mapping):
                sources.append(issue)
            sources.append(data)
        issue = root.get("issue")
        if isinstance(issue, Mapping):
            sources.append(issue)
        sources.append(root)
    return _dedupe_mappings(sources)


def _roots(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    roots: list[Mapping[str, Any]] = []

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext") or automation_info.get("trigger_context")
        if isinstance(trigger_context, Mapping):
            roots.append(trigger_context)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        roots.append(trigger_context)

    roots.append(event)
    return _dedupe_mappings(roots)


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        value = _clean_string(source.get("title"))
        if value:
            return value
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        for key in _ISSUE_ID_KEYS:
            value = _clean_string(source.get(key))
            if value:
                return value
    return None


def _prefixed_title(title: str) -> str:
    cleaned_title = title.strip()
    if _PREFIX_RE.match(cleaned_title):
        return cleaned_title
    return f"{TITLE_PREFIX}: {cleaned_title}"


def _normalize(value: Any) -> str:
    text = _clean_string(value)
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field_name(value: Any) -> str:
    normalized = _normalize(value)
    if normalized in {"workflowstate", "workflow state name"}:
        return "workflow state"
    return normalized


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _dedupe_mappings(sources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    deduped: list[Mapping[str, Any]] = []
    for source in sources:
        marker = id(source)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(source)
    return deduped


def main() -> int:
    """Read a JSON payload from stdin and print the title-update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
