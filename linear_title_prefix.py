"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
    "statusupdated",
    "stateupdated",
    "workflowstateupdated",
}
_UPDATE_TRIGGERS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_TRIGGER_KEYS = {"trigger", "webhookType", "event", "eventType", "action", "type"}
_UPDATED_FIELD_KEYS = {
    "updatedFields",
    "changedFields",
    "changes",
    "changed",
    "updatedFrom",
    "previousValues",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "targetStatus",
    "target_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(contexts, _ISSUE_ID_KEYS)
    title = _first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload layers, preferring outer metadata over issue data."""

    contexts: list[Mapping[str, Any]] = []
    for value in (
        event.get("triggerContext"),
        event,
        event.get("data"),
        _mapping(event.get("data")).get("issue") if isinstance(event.get("data"), Mapping) else None,
        event.get("issue"),
    ):
        if isinstance(value, Mapping):
            contexts.append(value)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    metadata_values = []
    has_generic_update = False

    for context in contexts:
        for key, value in context.items():
            if key in _TRIGGER_KEYS and isinstance(value, str):
                normalized = _compact(value)
                metadata_values.append(normalized)
                if normalized in _UPDATE_TRIGGERS:
                    has_generic_update = True

    if any(token in value for value in metadata_values for token in _DIRECT_STATUS_CHANGE_TRIGGERS):
        return True

    return has_generic_update and _has_status_field_change(contexts)


def _has_status_field_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if key not in context:
                continue
            if _contains_status_field(context[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _compact(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_compact(key) in _STATUS_FIELD_NAMES for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit_status = _first_string(context_list, _NEW_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    for context in context_list:
        for key in _STATUS_KEYS:
            status = _status_value(context.get(key))
            if status:
                return status
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string([value], ("name", "title"))
    return None


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _compact(value: str) -> str:
    return _normalize(value).replace(" ", "")


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
