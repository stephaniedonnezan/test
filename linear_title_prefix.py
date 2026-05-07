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
    """Return a Linear title update action when an issue moves to research.

    Cursor automation webhook payloads can be flat or nested below
    ``triggerContext``/``data``/``payload``/``issue``. This helper normalizes
    those shapes and stays idempotent by skipping titles that are already
    prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_changed(payload):
        return None

    new_status = _new_status(payload)
    if _normalize(new_status) != "to research":
        return None

    issue_id = _first_value(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_value(payload, ("title",))
    if issue_id is None or title is None:
        return None

    issue_id_text = str(issue_id).strip()
    title_text = str(title).strip()
    if not issue_id_text or not title_text:
        return None

    if _has_research_prefix(title_text):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id_text,
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title_text}",
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
        if normalized == "status changed" or normalized.endswith(" status changed"):
            return True
    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    status = _first_value(payload, ("newStatus", "new_status", "newState", "new_state", "status"))
    if status is not None:
        return status

    state = payload.get("state")
    if isinstance(state, Mapping):
        return _first_value(state, ("name", "title"))
    return None


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value)).strip().lower()
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())
