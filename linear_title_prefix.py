"""Build Linear issue title updates for research-status transitions.

The automation layer can pass either a flat Cursor trigger payload or a
Linear-style nested webhook payload. This module keeps the decision pure: it
returns the title update action to perform, or ``None`` when no update is due.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "statustype",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The returned shape is intentionally small so callers can map it to their
    Linear update primitive:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    scopes = _payload_scopes(event)
    if not _is_status_change_event(event):
        return None

    if _normalize(_new_status(scopes)) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(scopes, ("issueId", "issue_id", "identifier", "id"))
    title = _first_text(scopes, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _payload_scopes(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/trigger containers, ordered by specificity."""

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue") or _mapping_at(data, "issue")

    scopes: list[Mapping[str, Any]] = []
    for scope in (trigger_context, issue, data, event):
        if scope and scope not in scopes:
            scopes.append(scope)
    return scopes


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _normalize(value)
        for value in _values_for_keys(
            event,
            ("trigger", "webhookType", "action", "type", "event", "eventType"),
        )
    }

    if trigger_tokens & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_tokens & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "changedFields",
        "changed_fields",
        "updated",
        "changes",
        "updatedFrom",
        "previousValues",
    ):
        for value in _values_for_keys(event, (key,)):
            if _field_names_include_status(value):
                return True
    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in value.keys())

    if isinstance(value, Iterable):
        return any(_field_names_include_status(item) for item in value)

    return False


def _new_status(scopes: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(
        scopes,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
            "status",
        ),
    )
    if explicit_status:
        return explicit_status

    for scope in scopes:
        for key in ("state", "workflowState", "workflow_state", "status"):
            nested = _mapping_at(scope, key)
            if nested:
                nested_name = _first_text((nested,), ("name", "title"))
                if nested_name:
                    return nested_name

    return None


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not mapping:
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _first_text(scopes: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for scope in scopes:
        for key in keys:
            value = scope.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _values_for_keys(value: Any, keys: Iterable[str]) -> Iterable[Any]:
    key_set = set(keys)
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in key_set:
                yield item
            yield from _values_for_keys(item, key_set)
    elif isinstance(value, list):
        for item in value:
            yield from _values_for_keys(item, key_set)


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value).lower()


def main() -> int:
    event = json.load(sys.stdin)
    json.dump(build_issue_title_update(event), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
