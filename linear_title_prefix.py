"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_changed(payload):
        return None

    if _normalize(_new_status(payload)) != "to research":
        return None

    issue_id = _first_text(payload, "issueId", "issue_id", "id", "identifier")
    title = _first_text(payload, "title")
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for layer in _payload_layers(event):
        payload.update(layer)
    return payload


def _payload_layers(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    layers: list[Mapping[str, Any]] = []
    for key in ("issue", "data", "payload", "triggerContext"):
        layers.extend(_payload_layers(value.get(key)))
    layers.append(value)
    return layers


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
        normalized = _normalize(payload.get(key))
        if normalized in {"status changed", "issue updated"}:
            return True
        if normalized.endswith(" status changed"):
            return True
    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    status = _first_value(payload, "newStatus", "new_status", "newState", "new_state", "status")
    if status is not None:
        return status

    state = payload.get("state")
    if isinstance(state, Mapping):
        return _first_value(state, "name", "title")
    return None


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    value = _first_value(payload, *keys)
    if value is None:
        return None
    return str(value)


def _first_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value)).strip().casefold()
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())
