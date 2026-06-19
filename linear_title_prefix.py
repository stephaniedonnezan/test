"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_TRIGGERS = {"statuschanged", "statuschange"}
UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    if not _is_status_change(payloads):
        return None

    status = _changed_status(payloads)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payloads, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event)
    for key in ("triggerContext", "data", "issue"):
        add(event.get(key))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            add(trigger_context.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))

    return payloads


def _is_status_change(payloads: list[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_token(value)
        for payload in payloads
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    }

    if event_names & DIRECT_STATUS_TRIGGERS:
        return True

    if not event_names or event_names & UPDATE_TRIGGERS or "issue" in event_names:
        return _updated_fields_include_status(payloads) or _changes_include_status(payloads)

    return False


def _updated_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, str):
            updated_fields = [updated_fields]
        if isinstance(updated_fields, list) and any(
            _normalize_field_name(field) in STATUS_FIELDS for field in updated_fields
        ):
            return True
    return False


def _changes_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        changes = payload.get("changes") or payload.get("updated")
        if isinstance(changes, Mapping) and any(
            _normalize_field_name(field) in STATUS_FIELDS for field in changes
        ):
            return True
    return False


def _changed_status(payloads: list[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        value = _first_value(payloads, key)
        if value is not None:
            return _status_name(value)

    for payload in payloads:
        changes = payload.get("changes") or payload.get("updated")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return _status_name(_change_target(change))

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value(payloads, key)
        if value is not None:
            return _status_name(value)

    return None


def _change_target(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change
    for key in ("to", "new", "after", "newValue", "new_value"):
        if key in change:
            return change[key]
    return change


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            if key in value:
                return value[key]
    return value


def _first_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _first_value(payloads, key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _first_value(payloads: list[Mapping[str, Any]], key: str) -> Any:
    for payload in payloads:
        if key in payload:
            return payload[key]
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _normalize_words(value)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).casefold())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9_]+", "", _split_camel_case(value).casefold())


def _normalize_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", _split_camel_case(value).casefold()))


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
