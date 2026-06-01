"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The automation trigger can arrive as a flat Cursor `triggerContext` payload
    or as a nested Linear issue webhook. This function keeps the behavior small
    and deterministic: only recognized status-change events whose new status
    normalizes to "to research" produce an update action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = []
    for container in _candidate_containers(event):
        for key in ("trigger", "webhookType", "action", "type"):
            value = container.get(key)
            if value is not None:
                trigger_values.append(_normalize_token(_text(value)))

    if any(
        value in {"statuschanged", "statuschange", "issuestatuschanged"}
        for value in trigger_values
    ):
        return True

    if any(value in {"update", "updated", "issueupdated", "updatedissue"} for value in trigger_values):
        return _updated_status_fields(event)

    return False


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for container in _candidate_containers(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _has_status_field(container.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            value = container.get(key)
            if isinstance(value, Mapping) and _has_status_field(value.keys()):
                return True

    return False


def _has_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        names = value.keys()
    elif isinstance(value, (list, tuple, set)):
        names = value
    else:
        return False

    return any(_normalize_token(_text(name)) in _STATUS_FIELD_NAMES for name in names)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for keys in (explicit_keys, fallback_keys):
        for container in _candidate_containers(event):
            for key in keys:
                value = _text(container.get(key))
                if value:
                    return value

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for keys in (("issueId", "issue_id"), ("id", "identifier")):
        for container in _candidate_containers(event):
            for key in keys:
                value = _text(container.get(key))
                if value:
                    return value

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for container in _candidate_containers(event):
        value = _text(container.get("title"))
        if value:
            return value

    return None


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    _append_mapping(containers, trigger_context)
    _append_mapping(containers, issue)

    if isinstance(data, Mapping):
        _append_mapping(containers, data.get("issue"))
        _append_mapping(containers, data)

    _append_mapping(containers, event)
    return containers


def _append_mapping(containers: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in containers:
        containers.append(value)


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            text = _text(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = _split_words(value)
    return " ".join(words)


def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return value.lower().split()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True) if result is not None else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
