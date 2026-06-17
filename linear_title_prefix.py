"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _new_status(event, payload)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for candidate in (
        event.get("data"),
        _mapping(event.get("data")).get("issue"),
        event.get("issue"),
        event.get("triggerContext"),
        event,
    ):
        if isinstance(candidate, Mapping):
            payload.update(candidate)

    data = _mapping(event.get("data"))
    issue = _mapping(data.get("issue"))
    state = _mapping(issue.get("state"))
    workflow_state = _mapping(issue.get("workflowState"))
    if state.get("name") and "status" not in payload:
        payload["status"] = state.get("name")
    if workflow_state.get("name") and "status" not in payload:
        payload["status"] = workflow_state.get("name")

    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        event.get("trigger"),
        event.get("webhookType"),
        event.get("action"),
        event.get("type"),
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_identifier(value) for value in trigger_values if value}

    if normalized_triggers & {"statuschanged", "statechanged", "workflowstatechanged"}:
        return True

    if normalized_triggers & {"issueupdated", "updatedissue", "update", "updated"}:
        return _updated_fields_include_status(event) or _changes_include_status(event)

    return _updated_fields_include_status(event) or _changes_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for container in _containers(event):
        fields = container.get("updatedFields")
        if fields is None:
            fields = container.get("updated_fields")
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(fields, list):
            for field in fields:
                if _normalize_field(field) in STATUS_FIELDS:
                    return True
    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for container in _containers(event):
        changes = container.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _normalize_field(field) in STATUS_FIELDS:
                    return True
        if isinstance(changes, list):
            for change in changes:
                if isinstance(change, str) and _normalize_field(change) in STATUS_FIELDS:
                    return True
                if isinstance(change, Mapping):
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _normalize_field(field) in STATUS_FIELDS:
                        return True
    return False


def _new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    for container in _containers(event):
        value = _first_status_text(
            container,
            (
                "newStatus",
                "new_status",
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        if value:
            return value

    return _first_status_text(payload, ("newStatus", "new_status", "status", "state", "workflowState"))


def _containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            containers.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    return containers


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        if isinstance(value, int):
            return str(value)
    return None


def _first_status_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_field(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9 ]+", " ", _split_camel_case(value).lower()).strip()


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"[_-]+", " ", _split_camel_case(value))
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
