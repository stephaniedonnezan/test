"""Build title updates for Linear issues that move to research."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change(candidates):
        return None

    new_status = _new_status(candidates)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return issue-like payload sections from most to least specific."""
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            candidates.append(data_issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    if isinstance(data, Mapping):
        candidates.append(data)

    candidates.append(event)
    return candidates


def _is_status_change(candidates: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for candidate in candidates:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            normalized = _normalize_words(candidate.get(key))
            if not normalized:
                continue

            if normalized in {"status changed", "status change", "issue status changed"}:
                return True

            if normalized in {"issue updated", "updated issue"}:
                saw_issue_update = True

    return saw_issue_update and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_list_includes_status(candidate.get(key)):
                return True
    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in {"status", "state"}

    if isinstance(value, Mapping):
        return any(_field_list_includes_status(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_field_list_includes_status(item) for item in value)

    return False


def _new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        direct = _first_text(candidate, ("newStatus", "new_status", "status"))
        if direct:
            return direct

        state = candidate.get("state")
        if isinstance(state, Mapping):
            state_name = _text(state.get("name"))
            if state_name:
                return state_name

    return None


def _first_text(candidates: Iterable[Mapping[str, Any]] | Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    if isinstance(candidates, Mapping):
        iterable: Iterable[Mapping[str, Any]] = (candidates,)
    else:
        iterable = candidates

    for candidate in iterable:
        for key in keys:
            value = _text(candidate.get(key))
            if value:
                return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_words(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())
