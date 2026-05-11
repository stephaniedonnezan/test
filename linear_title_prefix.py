"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    layers = _payload_layers(event)

    if not _is_status_change(layers):
        return None

    new_status = _first_string(layers, ("newStatus", "new_status", "status"))
    if new_status is None:
        new_status = _first_nested_string(layers, ("state", "workflowState"), "name")

    if _normalize_label(new_status) != "to research":
        return None

    issue_id = _first_string(layers, ("issueId", "issue_id", "id", "identifier"))
    title = _first_string(layers, ("title",))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def _payload_layers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload locations in descending precedence."""
    layers: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        layers.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        layers.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            layers.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        layers.append(issue)

    layers.append(event)
    return layers


def _is_status_change(layers: list[Mapping[str, Any]]) -> bool:
    event_name = _first_string(layers, ("trigger", "action", "type"))
    if event_name is not None and _normalize_label(event_name) == "status changed":
        return True

    if event_name is not None and _normalize_label(event_name) in {
        "issue updated",
        "updated issue",
    }:
        return _updated_fields_include_status(layers)

    return False


def _updated_fields_include_status(layers: list[Mapping[str, Any]]) -> bool:
    for layer in layers:
        fields = layer.get("updatedFields")
        if isinstance(fields, str):
            fields = [fields]
        if not isinstance(fields, list):
            continue

        for field in fields:
            if _normalize_label(field) in {"status", "state", "workflow state"}:
                return True

    return False


def _first_string(
    layers: list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> str | None:
    for layer in layers:
        for key in keys:
            value = layer.get(key)
            if isinstance(value, str):
                return value
    return None


def _first_nested_string(
    layers: list[Mapping[str, Any]],
    parent_keys: tuple[str, ...],
    child_key: str,
) -> str | None:
    for layer in layers:
        for parent_key in parent_keys:
            parent = layer.get(parent_key)
            if not isinstance(parent, Mapping):
                continue
            value = parent.get(child_key)
            if isinstance(value, str):
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries)
    return " ".join(words_only.casefold().split())
