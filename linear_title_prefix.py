"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[^A-Za-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    if _normalize_text(_new_status(candidates)) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return issue-like payload sections from common automation/webhook shapes."""

    candidates: list[Mapping[str, Any]] = []

    def append(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    append(trigger_context)
    if isinstance(trigger_context, Mapping):
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            append(trigger_data.get("issue"))
            append(trigger_data)
        append(trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        append(data.get("issue"))
        append(data)

    append(event.get("issue"))
    append(event)
    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    update_event_seen = False

    for candidate in candidates:
        for key in ("trigger", "action", "type", "event", "webhookType", "webhook_type"):
            event_name = _normalize_text(candidate.get(key))
            if not event_name:
                continue

            if event_name in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "issue status changed",
                "workflow status changed",
                "workflow state changed",
            }:
                return True

            if event_name in {
                "update",
                "updated",
                "issue update",
                "issue updated",
                "update issue",
                "updated issue",
            }:
                update_event_seen = True

    return update_event_seen and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedFrom",
            "updated_from",
        ):
            if _field_list_includes_status(candidate.get(key)):
                return True

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in {
            "status",
            "status id",
            "state",
            "state id",
            "workflow status",
            "workflow state",
            "workflow state id",
        }

    if isinstance(value, Mapping):
        return any(_field_list_includes_status(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_field_list_includes_status(item) for item in value)

    return False


def _new_status(candidates: Iterable[Mapping[str, Any]]) -> Any:
    for candidate in candidates:
        for key in ("newStatus", "new_status", "newState", "new_state", "status", "state"):
            value = candidate.get(key)
            text = _state_name(value)
            if text:
                return text

    return None


def _state_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return value


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if value is None:
                continue

            text = str(value).strip()
            if text:
                return text

    return None


def _has_research_prefix(title: str) -> bool:
    normalized_title = _normalize_text(title)
    normalized_prefix = _normalize_text(PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix} "
    )


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return " ".join(text.casefold().split())
