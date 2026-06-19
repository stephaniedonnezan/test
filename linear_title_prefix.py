"""Build Linear title update actions for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = frozenset(("status", "state", "workflowstate", "workflow_state"))
STATUS_CHANGE_TRIGGERS = frozenset(
    (
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "state change",
        "statechanged",
        "workflowstate changed",
        "workflowstate change",
        "workflowstatechanged",
    )
)
ISSUE_UPDATE_TRIGGERS = frozenset(
    (
        "issue updated",
        "updated issue",
        "issue update",
        "update",
        "updated",
    )
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation webhook can arrive as the flat Cursor ``triggerContext`` object
    or as Linear's nested webhook payload. This function extracts the relevant
    fields conservatively and returns ``None`` when the payload is not a status
    change to the target research status.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _extract_new_status(payloads)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload layers from most specific trigger metadata to issue data."""

    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("status"))
        add(data.get("state"))
        add(data.get("workflowState"))

    add(event.get("issue"))
    add(event.get("status"))
    add(event.get("state"))
    add(event.get("workflowState"))

    return payloads


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_event_name(value)
        for payload in payloads
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(payloads)

    return not trigger_values and _changed_fields_include_status(payloads)


def _changed_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    return any(
        _field_names_include_status(payload.get(key))
        for payload in payloads
        for key in ("updatedFields", "updatedFieldNames", "changedFields")
    ) or any(_changes_include_status(payload.get("changes")) for payload in payloads)


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in STATUS_FIELD_NAMES
            or _field_names_include_status(nested_value)
            for key, nested_value in value.items()
        )

    if isinstance(value, list | tuple | set):
        return any(_field_names_include_status(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in STATUS_FIELD_NAMES
            or (
                isinstance(change, Mapping)
                and _normalize_field_name(change.get("field")) in STATUS_FIELD_NAMES
            )
            for key, change in value.items()
        )

    if isinstance(value, list | tuple | set):
        return any(
            isinstance(change, Mapping)
            and _normalize_field_name(change.get("field") or change.get("name"))
            in STATUS_FIELD_NAMES
            for change in value
        )

    return False


def _extract_new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(
        payloads,
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
        ),
    )
    if explicit_status:
        return explicit_status

    changed_status = _status_from_changes(payloads)
    if changed_status:
        return changed_status

    return _first_status_object_name(payloads) or _first_text(payloads, ("status", "state", "workflowState"))


def _status_from_changes(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        changes = payload.get("changes")
        status = _status_from_change_mapping(changes)
        if status:
            return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                status = _change_target_value(change)
                if status:
                    return status

        for change in value.values():
            if not isinstance(change, Mapping):
                continue
            if _normalize_field_name(change.get("field")) in STATUS_FIELD_NAMES:
                status = _change_target_value(change)
                if status:
                    return status

    if isinstance(value, list | tuple | set):
        for change in value:
            if not isinstance(change, Mapping):
                continue
            if _normalize_field_name(change.get("field") or change.get("name")) in STATUS_FIELD_NAMES:
                status = _change_target_value(change)
                if status:
                    return status

    return None


def _change_target_value(change: Any) -> str | None:
    if not isinstance(change, Mapping):
        return _text(change)

    for key in ("to", "toValue", "newValue", "after", "new", "value"):
        status = _status_value_to_text(change.get(key))
        if status:
            return status

    return None


def _status_value_to_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text:
                return text
        return None

    return _text(value)


def _first_status_object_name(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        for key in ("status", "state", "workflowState"):
            status = _status_value_to_text(payload.get(key))
            if status:
                return status
    return None


def _first_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            text = _text(payload.get(key))
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_event_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_status(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
