"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
    "issue status change",
    "issue status changed",
    "issue state change",
    "issue state changed",
}

_UPDATE_ACTIONS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "status name",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The automation payloads used in tests and production can be flat,
    wrapped in ``triggerContext``, or resemble Linear webhooks with issue
    data nested below ``data``/``issue``. This function keeps the public
    output intentionally small so the caller can decide how to execute it.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    if not _is_status_change(payloads):
        return None

    if _normalize_phrase(_new_status(payloads)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(_issue_value(payloads, ("id", "issueId", "issue_id", "identifier")))
    title = _first_text(_issue_value(payloads, ("title", "name")))

    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payloads.append(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                payloads.append(nested_issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("node", "resource"):
            value = data.get(key)
            if isinstance(value, Mapping):
                payloads.append(value)

    return payloads


def _is_status_change(payloads: Iterable[Mapping[str, Any]]) -> bool:
    update_action_seen = False
    status_field_seen = False

    for payload in payloads:
        for key in ("trigger", "event", "webhookType", "webhook_type", "action", "type"):
            value = payload.get(key)
            normalized = _normalize_phrase(value)
            if normalized in _STATUS_CHANGE_TRIGGERS:
                return True
            if key == "action" and normalized in _UPDATE_ACTIONS:
                update_action_seen = True

        if _has_status_field_marker(payload):
            status_field_seen = True

    return update_action_seen and status_field_seen


def _has_status_field_marker(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = payload.get(key)
        if isinstance(value, str):
            if _normalize_phrase(value) in _STATUS_FIELD_NAMES:
                return True
        elif isinstance(value, Iterable):
            for field in value:
                if _normalize_phrase(field) in _STATUS_FIELD_NAMES:
                    return True

    updated_from = payload.get("updatedFrom") or payload.get("updated_from")
    if isinstance(updated_from, Mapping):
        return any(_normalize_phrase(field) in _STATUS_FIELD_NAMES for field in updated_from)

    return False


def _new_status(payloads: Iterable[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for value in _values(payloads, explicit_keys):
        if _first_text((value,)):
            return _extract_name(value)

    for value in _values(payloads, fallback_keys):
        if _first_text((_extract_name(value),)):
            return _extract_name(value)

    return None


def _issue_value(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    payload_list = list(payloads)
    if not payload_list:
        return ()
    return _values([*payload_list[1:], payload_list[0]], keys)


def _values(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    for payload in payloads:
        for key in keys:
            if key in payload:
                yield payload[key]


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        value = _extract_name(value)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
