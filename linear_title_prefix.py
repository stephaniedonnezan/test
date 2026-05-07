"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TOKENS = {"statuschange", "statuschanged", "statechange", "statechanged"}
_ISSUE_UPDATED_TOKENS = {"issueupdated", "issueupdate", "updated"}
_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The Cursor automation payload may include data either at the top level,
    within ``triggerContext``, or inside Linear-style ``data.issue`` objects.
    This function keeps the integration boundary small by returning a simple
    action object for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    sources = list(_sources(event))

    if not _is_status_change(sources):
        return None

    if _normalized_status(_first_value(sources, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(sources, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_value(sources, ("title",)))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _sources(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload mappings from most general to most specific."""

    yield event

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    for parent_key in ("triggerContext", "data"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue

        for child_key in ("issue", "state"):
            child = parent.get(child_key)
            if isinstance(child, Mapping):
                yield child

    state = event.get("state")
    if isinstance(state, Mapping):
        yield state


def _is_status_change(sources: list[Mapping[str, Any]]) -> bool:
    trigger_values = list(_values(sources, ("trigger", "action", "type", "event", "webhookType")))
    if any(_normalized_token(value) in _STATUS_CHANGE_TOKENS for value in trigger_values):
        return True

    if any(_normalized_token(value) in _ISSUE_UPDATED_TOKENS for value in trigger_values):
        return _updated_fields_include_status(sources)

    return False


def _updated_fields_include_status(sources: list[Mapping[str, Any]]) -> bool:
    for value in _values(sources, ("updatedFields", "updated_fields", "changedFields", "changed_fields")):
        if isinstance(value, str):
            fields = (value,)
        elif isinstance(value, Iterable):
            fields = value
        else:
            continue

        if any(_normalized_token(field) in _STATUS_FIELD_TOKENS for field in fields):
            return True

    return False


def _first_value(sources: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value

        state = source.get("state")
        if isinstance(state, Mapping):
            name = state.get("name")
            if name is not None and ("status" in keys or "newStatus" in keys or "new_status" in keys):
                return name

    return None


def _values(sources: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Iterable[Any]:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                yield value


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _normalized_status(value: Any) -> str:
    value = _clean_string(value)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _normalized_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean_string(value).lower())
