"""Build title update actions for Linear issue status-change events."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to To Research.

    The automation runner passes Linear trigger payloads with slightly different
    shapes depending on the trigger source. This function accepts the flat
    Cursor automation shape as well as common nested Linear webhook shapes.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_changed_event(sources):
        return None

    if _normalize_text(_new_status(sources)) != "to research":
        return None

    issue_id = _first_text(sources, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(sources, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = _as_mapping(event.get("data"))
    trigger_context = _as_mapping(event.get("triggerContext"))
    event_issue = _as_mapping(event.get("issue"))
    data_issue = _as_mapping(data.get("issue")) if data else {}

    # Later sources have higher priority when callers provide duplicate fields.
    return [data_issue, event_issue, data, trigger_context, event]


def _is_status_changed_event(sources: list[Mapping[str, Any]]) -> bool:
    trigger_names = {
        _normalize_text(value)
        for value in _all_text_values(
            sources,
            ("trigger", "event", "eventType", "webhookType", "action", "type"),
        )
    }

    if trigger_names & {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }:
        return True

    if trigger_names & {"issue updated", "updated issue", "issue update", "update"}:
        return _updated_fields_include_status(sources)

    return False


def _new_status(sources: list[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(
        sources,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "status",
            "stateName",
            "workflowStateName",
        ),
    )
    if direct_status:
        return direct_status

    for key in ("state", "workflowState", "status"):
        nested_status = _first_nested_text(sources, key, ("name", "title", "label"))
        if nested_status:
            return nested_status

    return None


def _updated_fields_include_status(sources: list[Mapping[str, Any]]) -> bool:
    fields = _first_value(sources, ("updatedFields", "updated_fields", "changedFields"))
    if fields is None:
        return False

    if isinstance(fields, str):
        return _normalize_text(fields) in {"status", "state", "workflow state"}

    if isinstance(fields, Mapping):
        return any(
            _normalize_text(str(key)) in {"status", "state", "workflow state"}
            for key in fields.keys()
        )

    if isinstance(fields, (list, tuple, set)):
        return any(
            _normalize_text(str(field)) in {"status", "state", "workflow state"}
            for field in fields
        )

    return False


def _first_nested_text(
    sources: list[Mapping[str, Any]],
    outer_key: str,
    inner_keys: tuple[str, ...],
) -> str | None:
    for source in reversed(sources):
        nested = _as_mapping(source.get(outer_key))
        if not nested:
            continue

        value = _first_text([nested], inner_keys)
        if value:
            return value

    return None


def _first_text(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    value = _first_value(sources, keys)
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for nested_key in ("name", "title", "label"):
            nested_value = value.get(nested_key)
            if isinstance(nested_value, str):
                return nested_value

    return None


def _all_text_values(
    sources: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> list[str]:
    values: list[str] = []
    for source in reversed(sources):
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                values.append(value)
    return values


def _first_value(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for source in reversed(sources):
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())
