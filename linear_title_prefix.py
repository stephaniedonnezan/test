"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update for status changes to "to research".

    The automation trigger payloads used in tests and Cursor Automations can
    expose the issue metadata either at the top level, under ``triggerContext``,
    or nested in webhook-like ``data.issue`` objects. This function normalizes
    those common shapes and returns a declarative action for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize_status(_new_status(payload)) != TARGET_STATUS:
        return None

    title = _string_value(_first_present(payload, ("title", "name")))
    issue_id = _string_value(
        _first_present(payload, ("issueId", "issue_id", "identifier", "id"))
    )

    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the known nested Linear payload locations into one lookup map."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data)
        merge(data.get("issue"))
        _merge_state_name(payload, data.get("state"))

    merge(event.get("issue"))
    merge(event.get("triggerContext"))
    merge(event)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge(trigger_context.get("issue"))
        _merge_state_name(payload, trigger_context.get("state"))
        _merge_state_name(payload, trigger_context.get("status"))

    state = _first_present(payload, ("state", "status"))
    _merge_state_name(payload, state)

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_present(payload, ("trigger", "webhookType", "action", "type"))
    normalized_trigger = _normalize_token(trigger)
    if normalized_trigger in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
    }:
        return True

    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, (list, tuple, set)):
        normalized_fields = {_normalize_token(field) for field in updated_fields}
        if normalized_fields.intersection({"status", "state"}):
            return True

    return normalized_trigger == "issueupdated" and _new_status(payload) is not None


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "state.name",
        "status",
        "state",
    ):
        if key not in payload or payload[key] is None:
            continue

        value = payload[key]
        if isinstance(value, Mapping):
            nested_status = _first_present(value, ("name", "title"))
            if nested_status is not None:
                return nested_status
            continue

        return value

    return None


def _merge_state_name(payload: dict[str, Any], state: Any) -> None:
    if not isinstance(state, Mapping):
        return

    state_name = _first_present(state, ("name", "title"))
    if state_name is not None and "state.name" not in payload:
        payload["state.name"] = state_name


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    token = _normalize_token(value)
    if token is None:
        return None
    if token == "toresearch":
        return TARGET_STATUS
    return token


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    separated = _CAMEL_BOUNDARY_RE.sub(" ", value)
    return _SEPARATOR_RE.sub("", separated.casefold()) or None
