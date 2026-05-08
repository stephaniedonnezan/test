"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation trigger can provide issue data either at the top level, in a
    ``triggerContext`` object, or in Linear-style ``data.issue`` payloads.
    """

    if not isinstance(event, Mapping):
        return None

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(event.get("issue")) or _mapping(data.get("issue"))

    trigger_sources = (event, trigger_context, data)
    status_sources = tuple(source for source in (trigger_context, event, data, issue) if source)
    issue_sources = tuple(source for source in (issue, data, trigger_context, event) if source)

    if not _is_status_changed_event(trigger_sources):
        return None

    status = _first_label(status_sources, ("newStatus", "new_status", "newState", "new_state", "status", "state"))
    if _normalize_label(status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _first_text(issue_sources, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue_sources, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.casefold().startswith(RESEARCH_PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def _is_status_changed_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type"):
            event_name = _normalize_label(source.get(key))
            if _names_status_change(event_name):
                return True

        changed_fields = _changed_fields(source)
        if changed_fields and {"status", "state", "workflowstate", "workflow state"} & changed_fields:
            return True

    return False


def _names_status_change(event_name: str) -> bool:
    if not event_name:
        return False

    direct_names = {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "issue status changed",
        "issue state changed",
    }
    if event_name in direct_names:
        return True

    return ("status" in event_name or "state" in event_name) and (
        "changed" in event_name or "change" in event_name or "updated" in event_name or "update" in event_name
    )


def _changed_fields(source: Mapping[str, Any]) -> set[str]:
    fields = source.get("updatedFields") or source.get("updated_fields") or source.get("changedFields") or source.get(
        "changed_fields"
    )
    if fields is None:
        return set()

    if isinstance(fields, str):
        return {_normalize_label(fields).replace(" ", "")}

    if not isinstance(fields, Iterable):
        return set()

    normalized = set()
    for field in fields:
        label = _normalize_label(field)
        if label:
            normalized.add(label)
            normalized.add(label.replace(" ", ""))
    return normalized


def _first_label(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            label = _label(source.get(key))
            if label:
                return label
    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _label(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            text = _label(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _normalize_label(value: Any) -> str:
    label = _label(value)
    if not label:
        return ""

    label = _CAMEL_BOUNDARY.sub(" ", label)
    label = _NON_ALNUM.sub(" ", label)
    return " ".join(label.casefold().split())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
